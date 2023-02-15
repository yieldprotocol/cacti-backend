import json
import logging
import uuid

from websocket_server import WebsocketServer

import chat
import index
import system
import config
from database.models import (
    db_session, ChatSession, ChatMessage,
)
from utils import set_api_key


set_api_key()

system = config.initialized_system()

client_id_to_chat_history = {}


def new_client(client, server):
    session_id = uuid.uuid4()
    client_id_to_chat_history[client['id']] = chat.ChatHistory.new(session_id)


def client_left(client, server):
    client_id_to_chat_history.pop(client['id'])


def message_received(client, server, message):
    history = client_id_to_chat_history[client['id']]
    obj = json.loads(message)
    assert isinstance(obj, dict), obj
    actor = obj['actor']
    typ = obj['type']
    message = obj['payload']
    assert actor == 'user', obj

    # store user message
    chat_session = ChatSession.query.filter(ChatSession.id == history.session_id).one_or_none()
    if not chat_session:
        chat_session = ChatSession(id=history.session_id)
        db_session.add(chat_session)
        db_session.flush()
    chat_message = ChatMessage(
        actor=actor,
        type=typ,
        payload=message,
        chat_session_id=chat_session.id,
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
        )
        db_session.add(chat_message)
        db_session.commit()


server = WebsocketServer(host='0.0.0.0', port=9999, loglevel=logging.INFO)
server.set_fn_new_client(new_client)
server.set_fn_message_received(message_received)
server.set_fn_client_left(client_left)
server.run_forever()
