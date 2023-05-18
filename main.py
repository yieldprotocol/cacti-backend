import asyncio
from dataclasses import dataclass
from typing import Optional, Set

from fastapi import FastAPI, Request, Response, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import server
import chat
import env
import auth


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
    same_site='lax' if env.is_local() else 'none',
    https_only=not env.is_local(),
)


websockets: Set[WebSocket] = set()


@dataclass
class ClientState:
    chat_history: Optional[chat.ChatHistory] = None
    system_config_id: Optional[int] = None
    wallet_address: Optional[str] = None


@app.get("/nonce")
async def api_nonce(request: Request):
    return auth.api_nonce(request)


@app.post("/login")
async def api_login(request: Request, data: auth.AcceptJSON):
    return auth.api_login(request, data)


@app.post("/logout")
async def api_logout(request: Request):
    return auth.api_logout(request)


@app.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    websockets.add(websocket)
    try:
        await _handle_websocket(websocket)
    finally:
        websockets.remove(websocket)


async def _handle_websocket(websocket: WebSocket):
    client_state = ClientState()

    while True:
        try:
            message = await websocket.receive_text()

            # Fetch authenticated wallet address from the session cookies. If
            # not authenticated, this is None, and we handle this inside
            client_state.wallet_address = auth.fetch_authenticated_wallet_address(websocket)

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
