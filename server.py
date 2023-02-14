import json
import logging

from websocket_server import WebsocketServer

import chat
import index
import system
import config
from utils import set_api_key


set_api_key()

system = config.initialized_system()

client_id_to_chat_history = {}


def new_client(client, server):
    client_id_to_chat_history[client['id']] = chat.ChatHistory.new()


def client_left(client, server):
    client_id_to_chat_history.pop(client['id'])


def message_received(client, server, message):
    history = client_id_to_chat_history[client['id']]
    try:
        obj = json.loads(message)
        if isinstance(obj, dict) and obj.get('actor') == 'user' and obj.get('type') == 'text':
            message = obj['payload']
    except:
        # legacy message format, do nothing
        pass

    for resp in system.chat.receive_input(history, message):
        msg = json.dumps({
            'actor': resp.actor,
            'type': 'text',
            'payload': resp.response,
            'stillThinking': resp.still_thinking,
        })
        server.send_message(client, msg)


server = WebsocketServer(host='0.0.0.0', port=9999, loglevel=logging.INFO)
server.set_fn_new_client(new_client)
server.set_fn_message_received(message_received)
server.set_fn_client_left(client_left)
server.run_forever()
