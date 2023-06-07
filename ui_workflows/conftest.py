
from typing import Optional, Union

import requests
import pytest

import context
from utils import create_fork, remove_fork

@pytest.fixture(scope="module")
def setup_fork():
    # Before test
    #fork_id = create_fork()
    fork_id = "da6416f8-c838-4c8c-8215-47d2710df1ee"

    with context.with_request_context(None, None, wallet_chain_id=None, fork_id=fork_id):
        # Return to test function
        yield {"fork_id": fork_id}
    
    # After test
    #remove_fork(fork_id)