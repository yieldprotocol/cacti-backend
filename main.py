import asyncio
from dataclasses import dataclass
import json
import time
import traceback
from typing import Any, Dict, List, Optional, Set, Union

from fastapi import FastAPI, Request, Response, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import siwe

import server
import chat
import env


NONCE_EXPIRY_SECS = 60
AcceptJSON = Union[List, Dict, Any]  # a type that allows FastAPI to accept JSON objects


app = FastAPI()

origins = env.env_config['server']['origins']
host = env.env_config['server']['host']

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
async def api_nonce(request: Request):
    nonce = siwe.generate_nonce()
    request.session["nonce"] = nonce
    request.session["nonce_timestamp"] = time.time()
    return nonce


def _clear_session(request: Request):
    request.session["nonce"] = None
    request.session["nonce_timestamp"] = None
    request.session["wallet_address"] = None


@app.post("/login")
async def api_login(request: Request, data: AcceptJSON):
    if not data:
        _clear_session(request)
        return
    eip4361 = data.get("eip4361")
    signature = data.get("signature")
    if not eip4361 or not signature:
        _clear_session(request)
        return
    nonce = request.session.get("nonce")
    if not nonce:
        _clear_session(request)
        return
    nonce_timestamp = request.session.get("nonce_timestamp")
    if not nonce_timestamp:
        _clear_session(request)
        return
    if nonce_timestamp + NONCE_EXPIRY_SECS < time.time():
        _clear_session(request)
        return

    for python_key, javascript_key in [
            ('chain_id', 'chainId'),
            ('issued_at', 'issuedAt'),
            ('expiration_time', 'expirationTime'),
            ('not_before', 'notBefore'),
            ('request_id', 'requestId'),
    ]:
        if javascript_key in eip4361:
            eip4361[python_key] = eip4361.pop(javascript_key)

    try:
        # verify eip4361 and signature, get wallet address
        message = siwe.SiweMessage(message=eip4361)
        message.verify(signature, nonce=nonce, domain=host)
        assert message.statement == 'Sign me in to wc3 app', message.statement
        wallet_address = message.address
    except (
            siwe.VerificationError,
            siwe.InvalidSignature,
            siwe.ExpiredMessage,
            siwe.NotYetValidMessage,
            siwe.DomainMismatch,
            siwe.NonceMismatch,
            siwe.MalformedSession,
            AssertionError,
    ):
        traceback.print_exc()
        _clear_session(request)
        return

    # set authenticated wallet address in session
    request.session["wallet_address"] = wallet_address


@app.post("/logout")
async def api_logout(request: Request):
    _clear_session(request)


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
