import asyncio
from dataclasses import dataclass
import json
import secrets
from typing import Optional, Set

from fastapi import FastAPI, Request, Response, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import server
import chat
import env


app = FastAPI()

origins = env.env_config['server']['origins']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=env.env_config['server']['secret_key'],
    max_age=None,
    same_site='lax',
    https_only=False,
)


websockets: Set[WebSocket] = set()


@dataclass
class ClientState:
    chat_history: Optional[chat.ChatHistory] = None
    system_config_id: Optional[int] = None
    wallet_address: Optional[str] = None


@app.get("/nonce")
async def nonce(request: Request):
    # TODO: should there be a time-expiry?
    nonce = secrets.token_urlsafe()
    request.session["nonce"] = nonce
    return nonce


@app.post("/login")
async def login(request: Request, eip_string: str, signature: str):
    nonce = request.session.get("nonce")
    if not nonce:
        return

    # verify eip_string and signature, get wallet address
    # TODO

    # set authenticated wallet address is session
    request.session["wallet_address"] = wallet_address


@app.post("/logout")
async def logout(request: Request):
    request.session["nonce"] = None
    request.session["wallet_address"] = None


@app.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    websockets.add(websocket)
    try:
        await _handle_websocket(websocket)
    finally:
        websockets.remove(websocket)


async def _handle_websocket(websocket: WebSocket):
    # Get authenticated wallet address
    wallet_address = websocket.session.get("wallet_address")
    if not wallet_address:
        # Only allow authenticated wallet to chat
        await _handle_unauthenticated_wallet(websocket)
        return

    client_state = ClientState()

    while True:
        try:
            message = await websocket.receive_text()

            queue = asyncio.queues.Queue()

            def send_response(msg):
                queue.put_nowait(msg)

            async def process_message():
                await asyncio.to_thread(server.message_received, client_state, send_response, message)
                send_response(None)  # send sentinel

            async def send_responses():
                while True:
                    msg = await queue.get()
                    if msg is None:  # received sentinel
                        break
                    await websocket.send_text(msg)

            await asyncio.gather(process_message(), send_responses())

        except asyncio.CancelledError:
            break
        except WebSocketDisconnect:
            break


async def _handle_unauthenticated_wallet(websocket: WebSocket):
    while True:
        msg = json.dumps({
            'messageId': 0,
            'actor': 'bot',
            'type': 'text',
            'payload': 'Please connect your wallet to chat.',
            'stillThinking': False,
            'operation': 'create',
            'feedback': 'none',
        })
        await websocket.send_text(msg)
        message = await websocket.receive_text()


@app.on_event("startup")
async def startup_event():
    pass


@app.on_event("shutdown")
async def shutdown_event():
    # Cancel all active WebSocket tasks
    tasks = [asyncio.create_task(ws.close()) for ws in websockets]
    if tasks:
        await asyncio.gather(*tasks)


# Run with: ./start.sh
