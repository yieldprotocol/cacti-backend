import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from fastapi import FastAPI, Request, Response, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import server
import chat
import env
import auth
from app import share


app = FastAPI()

origins = env.env_config['server']['origins']
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
    secret_key=env.env_config['server']['secret_key'],
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


@app.get("/api/share_settings/{chat_session_id}")
async def api_share_settings(request: Request, chat_session_id: str) -> Dict:
    return share.get_settings(request, chat_session_id)


@app.put("/api/share_settings/{chat_session_id}")
async def api_share_settings_update(request: Request, chat_session_id: str, data: auth.AcceptJSON) -> bool:
    return share.update_settings(request, chat_session_id, data)


@app.post("/api/create_share/{chat_session_id}")
async def api_create_share(request: Request, chat_session_id: str, data: auth.AcceptJSON) -> Optional[str]:
    return share.create_share(request, chat_session_id, data)


@app.post("/api/import_share/{shared_session_id}")
async def api_import_share(request: Request, shared_session_id: str, data: auth.AcceptJSON) -> Optional[str]:
    return share.import_share(request, shared_session_id, data)


@app.get("/api/view_share/{shared_session_id}")
async def api_view_share(request: Request, shared_session_id: str) -> Dict:
    return share.view_share(request, shared_session_id)


@app.put("/api/update_share/{shared_session_id}")
async def api_update_share(request: Request, shared_session_id: str, data: auth.AcceptJSON) -> bool:
    return share.update_share(request, shared_session_id, data)


@app.get("/api/chats")
async def api_chats(request: Request) -> Dict:
    return share.get_visible_chats(request)


@app.get("/api/shares")
async def api_shares(request: Request) -> Dict:
    return share.get_visible_shares(request)


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
