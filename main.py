import env
import os
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from fastapi import FastAPI, Request, Response, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import server
import chat
import auth
from app import chat as app_chat
from app import share as app_share


app = FastAPI()

origins = os.environ['SERVER_ORIGINS'].split(',')

cookie_name = 'session' if env.is_local() else '__Secure-session'

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    session_cookie=cookie_name,
    secret_key=os.environ['SERVER_SECRET_KEY'],
    max_age=30 * 24 * 60 * 60,  # 30 days, match NextAuth
    same_site='lax' if env.is_local() else 'none',
    https_only=not env.is_local(),
)


@app.middleware("http")
async def handle_unset_session_cookie(request: Request, call_next: Any):
    # This custom middleware will unset the session cookie if it is not
    # a route associated with authentication. This will not clear an
    # existing session cookie, but merely ensures the response does
    # not call set-cookie for the session cookie if it is not relevant.
    # As reported in https://github.com/encode/starlette/issues/828 and
    # https://github.com/encode/starlette/issues/2019, Starlette will
    # (re)set the session cookie every time to extend the session.
    # However, when we first login, we might issue a GET request (e.g.
    # for /api/chats) while the /login POST request is still in-flight,
    # leading to our backend session cookie being clobbered due to
    # the race between these 2 requests (GET request finishes later but
    # does not have the session cookie updated with login data).
    should_unset_cookie = request['path'] not in ('/nonce', '/login', '/logout')
    response = await call_next(request)
    updated_headers = []
    if should_unset_cookie:
        for key, value in response.raw_headers:
            if key == b'set-cookie' and value.startswith(f'{cookie_name}='.encode()):
                continue
            updated_headers.append((key, value))
        response.raw_headers = updated_headers
    return response


websockets: Set[WebSocket] = set()


@dataclass
class ClientState:
    chat_history: Optional[chat.ChatHistory] = None
    system_config_id: Optional[int] = None
    wallet_address: Optional[str] = None
    user_id: Optional[str] = None


@app.get("/nonce")
async def api_nonce(request: Request):
    return auth.api_nonce(request)


@app.post("/login")
async def api_login(request: Request, data: auth.AcceptJSON):
    return auth.api_login(request, data)


@app.post("/logout")
async def api_logout(request: Request):
    return auth.api_logout(request)


@app.get("/api/chats")
async def api_chats_list(request: Request) -> Dict:
    return app_chat.list_chats(request)


@app.post("/api/chats")
async def api_chat_import(request: Request, data: auth.AcceptJSON) -> Optional[str]:
    return app_chat.import_chat_from_share(request, data)


@app.get("/api/chats/{chat_session_id}")
async def api_chat_get(request: Request, chat_session_id: str) -> Dict:
    # TODO: for now these only deal with chat settings, not messages of chat
    return app_chat.get_settings(request, chat_session_id)


@app.put("/api/chats/{chat_session_id}")
async def api_chat_put(request: Request, chat_session_id: str, data: auth.AcceptJSON) -> bool:
    # TODO: for now these only deal with chat settings, not messages of chat
    return app_chat.update_settings(request, chat_session_id, data)


@app.delete("/api/chats/{chat_session_id}")
async def api_chat_delete(request: Request, chat_session_id: str) -> bool:
    return app_chat.delete_chat(request, chat_session_id)


@app.get("/api/shares")
async def api_shares_list(request: Request) -> Dict:
    return app_share.list_shares(request)


@app.post("/api/shares")
async def api_share_create(request: Request, data: auth.AcceptJSON) -> Optional[str]:
    return app_share.create_share(request, data)


@app.get("/api/shares/{shared_session_id}")
async def api_share_get(request: Request, shared_session_id: str) -> Dict:
    return app_share.view_share(request, shared_session_id)


@app.put("/api/shares/{shared_session_id}")
async def api_share_put(request: Request, shared_session_id: str, data: auth.AcceptJSON) -> bool:
    return app_share.update_share(request, shared_session_id, data)


@app.delete("/api/shares/{shared_session_id}")
async def api_share_delete(request: Request, shared_session_id: str) -> bool:
    return app_share.delete_share(request, shared_session_id)


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
            client_state.user_id = auth.fetch_authenticated_user_id(websocket)

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
