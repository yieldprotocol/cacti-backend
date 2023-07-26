import functools
import json
import time
import traceback

from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import Request, WebSocket
import siwe

from utils import SERVER_HOST
from database import utils as db_utils
from database.models import (
    db_session, User, Wallet, UserWallet,
    ChatSession, ChatMessage, ChatMessageFeedback,
    SystemConfig,
)


NONCE_EXPIRY_SECS = 60 * 60  # one hour
AcceptJSON = Union[List, Dict, Any]  # a type that allows FastAPI to accept JSON objects
host = SERVER_HOST


def api_nonce(request: Request) -> str:
    """Returns generated nonce for signature verification on frontend.

    Also stores the nonce with the session cookie.

    """
    nonce = siwe.generate_nonce()
    request.session["nonce"] = nonce
    request.session["nonce_timestamp"] = time.time()
    nonce = request.session.get("nonce")
    nonce_timestamp = request.session.get("nonce_timestamp")
    return nonce


def api_login(request: Request, data: AcceptJSON) -> Optional[bool]:
    """Handles backend login. Returns true if successful, None otherwise.

    Side-effect(s):
    - sets session cookie with the wallet address if authenticated.
    - clears session cookie if not.

    """
    if not data:
        _clear_session(request)
        return
    eip4361 = data.get("eip4361")
    signature = data.get("signature")
    if not eip4361 or not signature:
        print('missing eip message or signature')
        _clear_session(request)
        return

    eip4361 = json.loads(eip4361)
    for python_key, javascript_key in [
            ('chain_id', 'chainId'),
            ('issued_at', 'issuedAt'),
            ('expiration_time', 'expirationTime'),
            ('not_before', 'notBefore'),
            ('request_id', 'requestId'),
    ]:
        if javascript_key in eip4361:
            eip4361[python_key] = eip4361.pop(javascript_key)

    # check if we are already logged in, and it matches the address in the message
    wallet_address = request.session.get("wallet_address")
    if wallet_address and eip4361.get('address') == wallet_address:
        print('wallet already authenticated', wallet_address)
        # don't need to do anything, we only clear cookies if we explicitly log out
        return True

    nonce = request.session.get("nonce")
    nonce_timestamp = request.session.get("nonce_timestamp")
    if not nonce or not nonce_timestamp:
        print('missing nonce or timestamp')
        _clear_session(request)
        return
    if nonce_timestamp + NONCE_EXPIRY_SECS < time.time():
        print('expired nonce')
        _clear_session(request)
        return

    try:
        # verify eip4361 and signature, get wallet address
        message = siwe.SiweMessage(message=eip4361)
        message.verify(signature, nonce=nonce, domain=host)
        assert message.statement == 'Sign me in to Cacti', message.statement
        assert message.address, message.address
        wallet_address = message.address
        print('authenticated wallet', wallet_address)
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

    # determine the user id
    user_id = _get_or_create_user_id_for_wallet_address(wallet_address)

    # set authenticated wallet address in session
    request.session["wallet_address"] = wallet_address
    request.session["user_id"] = user_id
    return True


@db_utils.close_db_session()
def _get_or_create_user_id_for_wallet_address(wallet_address: str) -> str:
    need_commit = False

    # First check if we know of this wallet, if not create it in the db
    wallet = Wallet.query.filter(Wallet.wallet_address == wallet_address).one_or_none()
    if not wallet:
        wallet = Wallet(wallet_address=wallet_address)
        db_session.add(wallet)
        db_session.flush()
        need_commit = True

    # Find the user for a given wallet
    user_wallet = UserWallet.query.filter(UserWallet.wallet_id == wallet.id).one_or_none()
    if not user_wallet:
        # Create a notion of a user if we don't have one yet
        # TODO: this needs to change if we support other OAuth mechanisms besides SIWE,
        # because we assume 1:1 mapping between user-wallet for now, which changes with
        # a different auth mechanism, where we might already know of the user and should
        # associate the existing user with this new wallet address.
        user = User()
        db_session.add(user)
        db_session.flush()

        user_wallet = UserWallet(user_id=user.id, wallet_id=wallet.id)
        db_session.add(user_wallet)
        db_session.flush()
        need_commit = True

    if need_commit:
        db_session.commit()

    # Now we should have the user id to associate with our session
    # Return as string not UUID object
    return str(user_wallet.user_id)


def api_logout(request: Request) -> bool:
    """Handles logging out the user by clearing the session cookies."""
    _clear_session(request)
    return True


def fetch_authenticated_wallet_address(request: Union[Request, WebSocket]) -> Optional[str]:
    return request.session.get("wallet_address")


def fetch_authenticated_user_id(request: Union[Request, WebSocket]) -> Optional[str]:
    return request.session.get("user_id")


def _clear_session(request: Request) -> None:
    request.session.pop("nonce", None)
    request.session.pop("nonce_timestamp", None)
    request.session.pop("wallet_address", None)
    request.session.pop("user_id", None)


def authenticate_user_id() -> Callable:
    """Decorator that passes in the currently authenticated user id, if any, as a kwarg to function."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapped_fn(*args: Any, **kwargs: Any) -> Any:
            # find request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            assert request is not None, f'expecting Request object to be passed into function: {fn.__name__}'
            user_id = fetch_authenticated_user_id(request)
            return fn(*args, user_id=user_id, **kwargs)
        return wrapped_fn
    return decorator
