import json
import logging
from websocket_server import WebsocketServer
import chat
from utils import set_api_key

set_api_key()


client_id_to_chat = {}

def new_client(client, server):
    client_id_to_chat[client['id']] = chat.new_chat()

def client_left(client, server):
    client_id_to_chat.pop(client['id'])

def message_received(client, server, message):
    client_chat = client_id_to_chat[client['id']]
    try:
        obj = json.loads(message)
        if isinstance(obj, dict) and obj.get('actor') == 'user' and obj.get('type') == 'text':
            message = obj['payload']
    except:
        # legacy message format, do nothing
        pass
    r = client_chat.chat(message)
    server.send_message(client, r)


server = WebsocketServer(host='0.0.0.0', port=9999, loglevel=logging.INFO)
server.set_fn_new_client(new_client)
server.set_fn_message_received(message_received)
server.set_fn_client_left(client_left)
server.run_forever()
