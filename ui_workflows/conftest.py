
from typing import Optional, Union

import requests
import pytest

import context
from utils import create_fork, remove_fork, TEST_TENDERLY_FORK_ID

@pytest.fixture(scope="module")
def setup_fork():
    # Before test
    fork_id = TEST_TENDERLY_FORK_ID or create_fork()

    with context.with_request_context(None, None, wallet_chain_id=None, fork_id=fork_id):
        # Return to test function
        yield {"fork_id": fork_id}
    
    # After test
    if not TEST_TENDERLY_FORK_ID:
        remove_fork(fork_id)