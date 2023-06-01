from typing import Dict
import json
import logging
logging.basicConfig(level=logging.INFO)
import uuid
from urllib.parse import urlparse, parse_qs

from sqlalchemy import func

import chat
import index
import system
import config
from database import utils as db_utils
from database.models import (
    db_session, FeedbackStatus,
    ChatSession, ChatMessage, ChatMessageFeedback,
    SystemConfig,
)
from utils import set_api_key
from ui_workflows.multistep_handler import process_multistep_workflow
import context

set_api_key()


# in-memory mapping of system config id to initialized systems
_system_config_id_to_system: Dict[int, system.System] = {}


def _get_system(system_config_id):
    global _system_config_id_to_system
    system = _system_config_id_to_system.get(system_config_id)
    if not system:
        system_config = SystemConfig.query.get(system_config_id)
        system = _register_system(system_config.id, system_config.json)
    return system


def _register_system(system_config_id, system_config_json):
    global _system_config_id_to_system
    system = config.initialize_system(system_config_json)
    _system_config_id_to_system[system_config_id] = system
    return system


@db_utils.close_db_session()
def _get_default_system_config_id():
    # we query the db but return the identifier to store, so that we can still
    # reference the id even after the session has been closed.
    default_system_config = SystemConfig.query.filter_by(json=config.default_config).one_or_none()
    if not default_system_config:
        default_system_config = SystemConfig(json=config.default_config)
        db_session.add(default_system_config)
        db_session.commit()
    print(f'The default system config id is: {default_system_config.id}')
    _register_system(default_system_config.id, default_system_config.json)
    return default_system_config.id

default_system_config_id = _get_default_system_config_id()



def _load_existing_history_and_messages(session_id):
    """Given an existing session_id, recreate the ChatHistory instance along with the individual Messages"""
    history = chat.ChatHistory.new(session_id)
    messages = []

    for message in ChatMessage.query.filter(ChatMessage.chat_session_id == session_id).order_by(ChatMessage.sequence_number, ChatMessage.created).all():
        messages.append(message)

        # register user/bot messages to history
        if message.type == 'text':
            if message.actor == 'user':
                history.add_user_message(message.payload, message_id=message.id)
            elif message.actor == 'bot':
                history.add_bot_message(message.payload, message_id=message.id)
            elif message.actor == 'system':
                history.add_system_message(message.payload, message_id=message.id)
            elif message.actor == 'commenter':
                history.add_commenter_message(message.payload, message_id=message.id)
            else:
                assert 0, f'unrecognized actor: {message.actor}'

    return history, messages


def _ensure_authenticated(client_state, send_response):
    if client_state.wallet_address:
        return True
    msg = json.dumps({
        'messageId': 0,
        'actor': 'bot',
        'type': 'text',
        'payload': 'Please connect your wallet to chat.',
        'stillThinking': False,
        'operation': 'create',
        'feedback': 'none',
    })
    send_response(msg)
    return False


@db_utils.close_db_session()
def message_received(client_state, send_response, message):
    if not _ensure_authenticated(client_state, send_response):
        return

    obj = json.loads(message)
    assert isinstance(obj, dict), obj
    actor = obj['actor']
    typ = obj['type']
    payload = obj['payload']

    # set system config used by client
    if typ == 'cfg':
        if 'systemConfigId' in payload and bool(payload['systemConfigId']):
            system_config_id = int(payload['systemConfigId'])
            client_state.system_config_id = system_config_id
        return

    history = client_state.chat_history
    system_config_id = client_state.system_config_id or default_system_config_id
    system = _get_system(system_config_id)

    # resume an existing chat history session, given a session id
    if typ == 'init':
        assert history is None, f'received a session resume request for existing session {history.session_id}'

        # HACK: legacy payload is a query string of the format '?s=some_session_id', temporarily preserve backwards compatibility
        if isinstance(payload, str):
            # parse query string for session id
            params = parse_qs(urlparse(payload).query)
            session_id = uuid.UUID(params['s'][0])
            resume_from_message_id = None
        else:
            session_id = uuid.UUID(payload['sessionId'])
            resume_from_message_id = payload.get('resumeFromMessageId')

        # load DB stored chat history and associated messages
        history, messages = _load_existing_history_and_messages(session_id)
        assert client_state.chat_history is None
        client_state.chat_history = history

        # reconstruct the chat history for the client, starting right after resume_from_message_id
        if resume_from_message_id is None:
            message_start_idx = 0
        else:
            message_start_indexes = [i for i, message in enumerate(messages) if str(message.id) == resume_from_message_id]
            assert len(message_start_indexes) == 1, f'expected one message to match id {resume_from_message_id}, got {len(message_start_indexes)} for session {session_id}'
            message_start_idx = message_start_indexes[0] + 1

        for i in range(message_start_idx, len(messages)):
            message = messages[i]
            msg = json.dumps({
                'messageId': str(message.id),
                'actor': message.actor,
                'type': message.type,
                'payload': message.payload,
                'feedback': str(message.chat_message_feedback.feedback_status.name) if message.chat_message_feedback else 'none',
            })
            send_response(msg)
        return

    # first message received - first create a new session history instance
    if history is None:
        session_id = uuid.uuid4()
        history = chat.ChatHistory.new(session_id)
        assert client_state.chat_history is None
        client_state.chat_history = history

        # inform client of the newly created session id
        msg = json.dumps({
            'messageId': '',
            'actor': 'system',
            'type': 'uuid',
            'payload': str(session_id),
            'feedback': 'n/a',
        })
        send_response(msg)

    assert actor in ('user', 'commenter') or (actor == 'system' and (typ == 'replay-user-msg' or typ == 'multistep-workflow')), obj

    # set wallet address onto chat history prior to processing input
    history.wallet_address = client_state.wallet_address

    chat_session = ChatSession.query.filter(ChatSession.id == history.session_id).one_or_none()
    if not chat_session:
        chat_session = ChatSession(id=history.session_id)
        db_session.add(chat_session)
        db_session.flush()

    def send_message(resp, last_chat_message_id=None, before_message_id=None):
        """Send message function.

        This function is passed into the chat module, to be called when the
        server has something to send back to the client. It could be a full
        message, or a partial response to be appended to the end of the
        previous message. It could also be a different actor (e.g. 'system'
        instead of just the 'bot') sending the message.

        Parameters
        ----------
        last_chat_message_id: The id of the database record that should be
            updated, if specified. The caller of this function controls the
            logic of when a new record should be created (by passing a
            response with operation 'create'), or when one should be
            appended to or replaced (with 'append' and 'replace' respectively).
        before_message_id: The id of the database record before which we
            should be inserting our current message.

        Returns
        -------
        chat message id representing the row in the db that this message
        is being stored in.

        """
        nonlocal send_response

        # store response (if not streaming)
        if resp.operation in ('create', 'create_then_replace'):
            # figure out the current sequence number
            if before_message_id:
                before_seq_num = ChatMessage.query.get(before_message_id).sequence_number
                seq_num = (db_session.query(func.max(ChatMessage.sequence_number)).filter(ChatMessage.chat_session_id == chat_session.id, ChatMessage.sequence_number < before_seq_num).scalar() or 0) + 1
                if seq_num >= before_seq_num:
                    # bump sequence number of everything else
                    for message in ChatMessage.query.filter(ChatMessage.chat_session_id == chat_session.id, ChatMessage.sequence_number >= before_seq_num).all():
                        message.sequence_number += 1
                        db_session.add(message)
            else:
                seq_num = (db_session.query(func.max(ChatMessage.sequence_number)).filter(ChatMessage.chat_session_id == chat_session.id).scalar() or 0) + 1
            chat_message = ChatMessage(
                actor=resp.actor,
                type='text',
                payload=resp.response,
                sequence_number=seq_num,
                chat_session_id=chat_session.id,
                system_config_id=system_config_id,
            )
            db_session.add(chat_message)
            db_session.commit()
            chat_message_id = chat_message.id
        elif resp.operation == 'append':
            # don't write to db
            chat_message_id = last_chat_message_id
        elif resp.operation == 'replace':
            assert last_chat_message_id
            chat_message = ChatMessage.query.get(last_chat_message_id)
            chat_message.payload = resp.response
            db_session.add(chat_message)
            db_session.commit()
            chat_message_id = last_chat_message_id
        else:
            assert 0, f'unrecognized operation: {resp.operation}'

        before_message_id_kwargs = {'beforeMessageId': str(before_message_id)} if before_message_id is not None else {}
        msg = json.dumps({
            'messageId': str(chat_message_id),
            'actor': resp.actor,
            'type': 'text',
            'payload': resp.response,
            'stillThinking': resp.still_thinking,
            'operation': resp.operation,
            'feedback': 'none',
            **before_message_id_kwargs,
        })
        send_response(msg)

        return chat_message_id

    # Handle multi-step workflows
    if typ == 'multistep-workflow':
        with context.with_request_context(history.wallet_address, None):
            process_multistep_workflow(payload, send_message)
        return

    # check if it is an action
    if typ == 'action':
        action_type = obj['payload'].get('actionType', 'feedback')
        if action_type == 'feedback':
            chat_message_id = uuid.UUID(obj['payload']['messageId'])
            feedback_status = FeedbackStatus.__members__[obj['payload']['choice']]
            chat_message_feedback = ChatMessageFeedback.query.filter(ChatMessageFeedback.chat_message_id == chat_message_id).one_or_none()
            if chat_message_feedback:
                chat_message_feedback.feedback_status = feedback_status
            else:
                chat_message_feedback = ChatMessageFeedback(
                    chat_message_id=chat_message_id,
                    feedback_status=feedback_status,
                )
            db_session.add(chat_message_feedback)
        elif action_type == 'transaction':
            tx_hash = obj['payload']['hash']
            success = obj['payload'].get('success')
            if not success:
                error = obj['payload'].get('error')
            # store system message representing transaction outcome
            tx_message = f"Transaction with hash {tx_hash} "
            if success:
                tx_message += "succeeded."
            else:
                tx_message += "failed"
                if error:
                    tx_message += f" with error {error}."

            message_id = send_message(chat.Response(
                response=tx_message,
                still_thinking=False,
                actor='system',
                operation='create',
            ), last_chat_message_id=None)
            history.add_system_message(tx_message, message_id=message_id)
        elif action_type in ('edit', 'regenerate'):
            edit_message_id = uuid.UUID(obj['payload']['messageId'])
            chat_message = ChatMessage.query.get(edit_message_id)
            if action_type == 'edit':
                payload = obj['payload']['text']
                chat_message.payload = payload
            else:
                payload = chat_message.payload
            if chat_message.actor == 'user':
                before_message_id = history.find_next_human_message(edit_message_id)
                removed_message_ids = history.truncate_from_message(edit_message_id, before_message_id=before_message_id)
                for removed_id in removed_message_ids:
                    if removed_id == edit_message_id:  # don't remove the message being edited/regenerated from db
                        continue
                    db_session.delete(ChatMessage.query.get(removed_id))  # use this delete approach to have cascade
                db_session.commit()
                system.chat.receive_input(
                    history, payload, send_message,
                    message_id=edit_message_id,
                    before_message_id=before_message_id,
                )
        elif action_type == 'delete':
            delete_message_id = uuid.UUID(obj['payload']['messageId'])
            chat_message = ChatMessage.query.get(delete_message_id)
            before_message_id = history.find_next_human_message(delete_message_id)
            removed_message_ids = history.truncate_from_message(delete_message_id, before_message_id=before_message_id)
            for removed_id in removed_message_ids:
                db_session.delete(ChatMessage.query.get(removed_id))  # use this delete approach to have cascade
        else:
            assert 0, f'unrecognized action type: {action_type}'

        db_session.commit()
        return

    # NB: here this could be regular user message or a system message replay

    # store new user/commenter message
    still_thinking = True if actor == 'user' else False
    message_id = send_message(chat.Response(
        response=payload,
        still_thinking=still_thinking,
        actor=actor,
        # NB: the frontend already appends a placeholder message immediately
        # as part of an optimistic update for smooth UX purposes, but
        # that one does not have the message_id since that is only obtained
        # after a db write. Hence, we have a hybrid operation here, where we
        # do a 'create' behavior in the backend (create a message in the db),
        # but we do a 'replace' behavior in the frontend, to replace the
        # placeholder message with one that now contains the message_id. We
        # need message_id to be present on all user messages, so that when
        # they get edited, we know at which point to truncate subsequent
        # messages.
        operation='create_then_replace',
    ), last_chat_message_id=None)

    if actor == 'user':
        system.chat.receive_input(history, payload, send_message, message_id=message_id)

    db_session.commit()
