import json
import logging
import uuid
from urllib.parse import urlparse, parse_qs

from websocket_server import WebsocketServer

import chat
import index
import system
import config
from database.models import (
    db_session, ChatSession, ChatMessage, SystemConfig,
)
from utils import set_api_key


set_api_key()

system = config.initialized_system()

system_config = SystemConfig.query.filter_by(json=config.config).one_or_none()
if not system_config:
    system_config = SystemConfig(json=config.config)
    db_session.add(system_config)
    db_session.commit()


client_id_to_chat_history = {}


def new_client(client, server):
    client_id_to_chat_history[client['id']] = chat.ChatHistory.new()


def client_left(client, server):
    client_id_to_chat_history.pop(client['id'])


def message_received(client, server, message):
    history = client_id_to_chat_history[client['id']]
    obj = json.loads(message)
    assert isinstance(obj, dict), obj
    actor = obj['actor']
    typ = obj['type']
    message = obj['payload']

    # check if we need to assign a new session id from the server side
    send_history = False
    if not history.session_id:
        if typ == 'init':  # client gave us the session id
            # parse query string for session id
            q = parse_qs(urlparse(message).query)
            history.session_id = uuid.UUID(q['s'][0])
            send_history = True
        else:  # server assigns new session id, send to client
            history.session_id = uuid.uuid4()
            msg = json.dumps({
                'actor': 'system',
                'type': 'uuid',
                'payload': str(history.session_id),
            })
            server.send_message(client, msg)

    chat_session = ChatSession.query.filter(ChatSession.id == history.session_id).one_or_none()
    if not chat_session:
        chat_session = ChatSession(id=history.session_id)
        db_session.add(chat_session)
        db_session.flush()

    if send_history:
        last_user_message = None
        last_bot_message = None
        for message in ChatMessage.query.filter(ChatMessage.chat_session_id == history.session_id).order_by(ChatMessage.created).all():
            msg = json.dumps({
                'actor': message.actor,
                'type': message.type,
                'payload': message.payload,
            })
            server.send_message(client, msg)
            if message.actor == 'user' and message.type == 'text':
                # for now, only restore the last bot message as interaction
                if last_bot_message is not None:
                    assert last_user_message is not None
                    history.add_interaction(last_user_message, last_bot_message)
                    last_bot_message = None
                last_user_message = message.payload
            elif message.actor == 'bot' and message.type == 'text':
                last_bot_message = message.payload
        if last_bot_message is not None:
            assert last_user_message is not None
            history.add_interaction(last_user_message, last_bot_message)
        return

    assert actor == 'user', obj

    # store new user message
    chat_message = ChatMessage(
        actor=actor,
        type=typ,
        payload=message,
        chat_session_id=chat_session.id,
        system_config_id=system_config.id,
    )
    db_session.add(chat_message)
    db_session.commit()

    for resp in system.chat.receive_input(history, message):
        msg = json.dumps({
            'actor': resp.actor,
            'type': 'text',
            'payload': resp.response,
            'stillThinking': resp.still_thinking,
        })
        server.send_message(client, msg)

        # store response (if not streaming)
        chat_message = ChatMessage(
            actor=resp.actor,
            type='text',
            payload=resp.response,
            chat_session_id=chat_session.id,
            system_config_id=system_config.id,
        )
        db_session.add(chat_message)
        db_session.commit()


server = WebsocketServer(host='0.0.0.0', port=9999, loglevel=logging.INFO)
server.set_fn_new_client(new_client)
server.set_fn_message_received(message_received)
server.set_fn_client_left(client_left)
server.run_forever()
