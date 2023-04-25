from typing import Any, Optional
import contextlib
import threading


class _RequestContext(threading.local):
    wallet_address: Optional[str] = None
    user_chat_message_id: Optional[str] = None
    
_request_context = _RequestContext()


@contextlib.contextmanager
def with_request_context(wallet_address: str, user_chat_message_id: str) -> Any:
    global _request_context

    if _request_context.wallet_address is not None:
        raise RuntimeError('Request context already set')

    _request_context.wallet_address = wallet_address
    _request_context.user_chat_message_id = user_chat_message_id
    try:
        yield
    finally:
        _request_context.wallet_address = None
        _request_context.user_chat_message_id = None


def get_wallet_address() -> Optional[str]:
    global _request_context
    return _request_context.wallet_address

def get_user_chat_message_id() -> Optional[str]:
    global _request_context
    return _request_context.user_chat_message_id