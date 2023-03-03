from typing import Any, Optional
import contextlib
import threading


class _WalletState(threading.local):
    wallet_address: Optional[str] = None


_wallet_state = _WalletState()


@contextlib.contextmanager
def with_wallet_address(wallet_address: str) -> Any:
    global _wallet_state
    prev_wallet_address = _wallet_state.wallet_address
    _wallet_state.wallet_address = wallet_address
    try:
        yield
    finally:
        _wallet_state.wallet_address = prev_wallet_address


def get_wallet_address() -> Optional[str]:
    global _wallet_state
    return _wallet_state.wallet_address
