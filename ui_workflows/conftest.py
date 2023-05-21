
from typing import Optional, Union

import requests
import pytest

import context
from utils import create_fork, remove_fork

@pytest.fixture(scope="module")
def setup_fork():
    # Before test
    fork_id = create_fork()

    with context.with_request_context(None, None, fork_id=fork_id):
        # Return to test function
        yield {"fork_id": fork_id}
    
    # After test
    remove_fork(fork_id)