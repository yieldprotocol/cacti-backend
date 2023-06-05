import functools
from typing import Any, Callable

from .models import db_session


def close_db_session() -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapped_fn(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            finally:
                db_session.close()
        return wrapped_fn
    return decorator
