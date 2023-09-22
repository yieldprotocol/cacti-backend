import contextlib
import threading
from typing import Any, Optional

from utils import web3_provider

class _RequestContext(threading.local):
    wallet_address: Optional[str] = None
    user_chat_message_id: Optional[str] = None
    wallet_chain_id: Optional[str] = None
    fork_id: Optional[str] = None


_request_context = _RequestContext()

# TODO: Refactor references of with_request_context to set wallet_chain_id
@contextlib.contextmanager
def with_request_context(wallet_address: str, user_chat_message_id: str, wallet_chain_id: Optional[int] = 1, fork_id: Optional[str] = None) -> Any:
    global _request_context

    if _request_context.wallet_address is not None:
        raise RuntimeError('Request context already set')

    if (wallet_chain_id and fork_id) or (not wallet_chain_id and not fork_id):
        raise RuntimeError(
            "Must either set wallet chain ID or fork ID, but not both"
        )

    _request_context.wallet_address = wallet_address
    _request_context.user_chat_message_id = user_chat_message_id
    _request_context.wallet_chain_id = wallet_chain_id
    _request_context.fork_id = fork_id
    try:
        yield
    finally:
        _request_context.wallet_address = None
        _request_context.user_chat_message_id = None
        _request_context.wallet_chain_id = None
        _request_context.fork_id = None


def get_wallet_address() -> Optional[str]:
    global _request_context
    return _request_context.wallet_address

def get_wallet_chain_id() -> Optional[str]:
    global _request_context
    return _request_context.wallet_chain_id

def get_user_chat_message_id() -> Optional[str]:
    global _request_context
    return _request_context.user_chat_message_id

# TODO: Refactor - rename function to 'get_web3'
def get_web3_provider():
    """
    Return the appropriate web3 provider depending on Chain ID or Fork ID.
    Fork ID is only used in simulation/demo/testing and takes precedence over Chain ID as it is inherently based off a Chain ID

    TODO: refactor the rest of the code to use this function instead of utils.common.w3 as that is hardcoded to a default fork
    """
    global _request_context
    if _request_context.fork_id:
        return web3_provider.get_web3_provider_from_fork_id(_request_context.fork_id)
    elif _request_context.wallet_chain_id:
        return web3_provider.get_web3_from_chain_id(_request_context.wallet_chain_id)
    else:
        raise RuntimeError("Fork ID and Chain ID not set in request context")

def get_web3_fork_id():
    global _request_context
    if _request_context.fork_id:
        return _request_context.fork_id
    elif _request_context.wallet_chain_id:
        return web3_provider.get_fork_id_from_chain_id(_request_context.wallet_chain_id)
    else:
        raise RuntimeError("Fork ID and Chain ID not set in request context")

def get_web3_tenderly_fork_url():
    global _request_context
    if _request_context.fork_id:
        return web3_provider.get_fork_url(_request_context.fork_id)
    elif _request_context.wallet_chain_id:
        return web3_provider.get_fork_url_from_chain_id(_request_context.wallet_chain_id)
    else:
        raise RuntimeError("Fork ID and Chain ID not set in request context")
