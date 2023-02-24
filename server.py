import json
import logging
import uuid

from websocket_server import WebsocketServer

import chat
import index
import system
import config
from database.models import (
    db_session, FeedbackStatus,
    ChatSession, ChatMessage, ChatMessageFeedback,
    SystemConfig,
)
from utils import set_api_key


set_api_key()

system = config.initialized_system()

system_config = SystemConfig.query.filter_by(json=config.config).one_or_none()
if not system_config:
    system_config = SystemConfig(json=config.config)
    db_session.add(system_config)
    db_session.commit()


# in-memory mapping of connected clients to their associated ChatHistory instances
_client_id_to_chat_history = {}


def _register_client_history(client_id, history):
    global _client_id_to_chat_history
    assert client_id not in _client_id_to_chat_history
    _client_id_to_chat_history[client_id] = history


def _get_client_history(client_id):
    global _client_id_to_chat_history
    return _client_id_to_chat_history.get(client_id)


def _deregister_client_history(client_id):
    global _client_id_to_chat_history
    return _client_id_to_chat_history.pop(client_id, None)


def new_client(client, server):
    history = _get_client_history(client['id'])
    assert history is None, f'existing chat history session ${history.session_id} for new client connection'


def client_left(client, server):
    _deregister_client_history(client['id'])


def _load_existing_history_and_messages(session_id):
    """Given an existing session_id, recreate the ChatHistory instance along with the individual Messages"""
    history = chat.ChatHistory.new(session_id=session_id)
    messages = []

    last_user_message = None
    last_bot_message = None
    for message in ChatMessage.query.filter(ChatMessage.chat_session_id == session_id).order_by(ChatMessage.created).all():
        messages.append(message)

        # register user <-> bot interactions
        if message.type == 'text':
            if message.actor == 'user':
                # for now, only restore the last bot message as interaction
                if last_bot_message is not None:
                    assert last_user_message is not None
                    history.add_interaction(last_user_message, last_bot_message)
                    last_bot_message = None
                last_user_message = message.payload

            elif message.actor == 'bot':
                last_bot_message = message.payload

    if last_bot_message is not None:
        assert last_user_message is not None
        history.add_interaction(last_user_message, last_bot_message)

    return history, messages


def message_received(client, server, message):
    _message_received(client, server, message)
    db_session.close()


def _message_received(client, server, message):
    client_id = client['id']
    history = _get_client_history(client_id)
    obj = json.loads(message)
    assert isinstance(obj, dict), obj
    actor = obj['actor']
    typ = obj['type']
    payload = obj['payload']

    # resume an existing chat history session, given a session id
    if typ == 'init':
        assert history is None, f'received a session resume request for existing session ${history.session_id}'

        # parse query string for session id
        session_id = uuid.UUID(payload['sessionId'])
        resume_from_message_id = payload.get('resumeFromMessageId')

        # load DB stored chat history and associated messages
        history, messages = _load_existing_history_and_messages(session_id)
        _register_client_history(client_id, history)

        # reconstruct the chat history for the client, starting right after resume_from_message_id
        if resume_from_message_id is None:
            message_start_idx = 0
        else:
            message_start_indexes = [i for i, message in enumerate(messages) if message.id == resume_from_message_id]
            assert len(message_start_indexes) == 1, f'expected one message to match id ${resume_from_message_id}'
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
            server.send_message(client, msg)
        return

    # first message received - first create a new session history instance
    if history is None:
        session_id = uuid.uuid4()
        history = chat.ChatHistory.new(session_id=session_id)
        _register_client_history(client_id, history)

        # inform client of the newly created session id
        msg = json.dumps({
            'messageId': '',
            'actor': 'system',
            'type': 'uuid',
            'payload': str(session_id),
            'feedback': 'n/a',
        })
        server.send_message(client, msg)

    assert actor == 'user', obj

    chat_session = ChatSession.query.filter(ChatSession.id == history.session_id).one_or_none()
    if not chat_session:
        chat_session = ChatSession(id=history.session_id)
        db_session.add(chat_session)
        db_session.flush()

    # check if it is an action
    if typ == 'action':
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
        db_session.commit()
        return

    # store new user message
    chat_message = ChatMessage(
        actor=actor,
        type=typ,
        payload=payload,
        chat_session_id=chat_session.id,
        system_config_id=system_config.id,
    )
    db_session.add(chat_message)
    db_session.commit()

    def send_message(resp, last_chat_message_id=None):
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

        Returns
        -------
        chat message id representing the row in the db that this message
        is being stored in.

        """

        # store response (if not streaming)
        if resp.operation == 'create':
            chat_message = ChatMessage(
                actor=resp.actor,
                type='text',
                payload=resp.response,
                chat_session_id=chat_session.id,
                system_config_id=system_config.id,
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

        msg = json.dumps({
            'messageId': str(chat_message_id),
            'actor': resp.actor,
            'type': 'text',
            'payload': resp.response,
            'stillThinking': resp.still_thinking,
            'operation': resp.operation,
            'feedback': 'none',
        })
        server.send_message(client, msg)

        return chat_message_id

    system.chat.receive_input(history, message, send_message)


server = WebsocketServer(host='0.0.0.0', port=9999, loglevel=logging.INFO)
server.set_fn_new_client(new_client)
server.set_fn_message_received(message_received)
server.set_fn_client_left(client_left)
server.run_forever()
