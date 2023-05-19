
"""
Test for validating that workflow should return an error if token not found in user's profile
"""

import re

from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from ....base import process_result_and_simulate_tx, fetch_multistep_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID

from ..aave_supply_ui_workflow import AaveSupplyUIWorkflow

from utils import w3, Web3

# Invoke this with python3 -m pytest -s -k "test_ui_aave_supply_no_token_error"
def test_ui_aave_supply_no_token_error():
    token = "XXYYZZ"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    # Step 1 - Try to initiate approval
    multistep_result = AaveSupplyUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    assert multistep_result.status == "error"
    assert multistep_result.error_msg == "Token XXYYZZ not found on user's profile"
