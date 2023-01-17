import logging
from websocket_server import WebsocketServer

client_id_to_chat_history={}

def new_client(client, server):
    client_id_to_chat_history[client['id']]=[]

def client_left(client, server):
    client_id_to_chat_history.pop(client['id'])

def message_received(client, server, message):
    from chat import chat
    r,h=chat(message,client_id_to_chat_history[client['id']])
    client_id_to_chat_history[client['id']] = h
    server.send_message(client,r)


server = WebsocketServer(host='127.0.0.1', port=9999, loglevel=logging.INFO)
server.set_fn_new_client(new_client)
server.set_fn_message_received(message_received)
server.set_fn_client_left(client_left)
server.run_forever()
