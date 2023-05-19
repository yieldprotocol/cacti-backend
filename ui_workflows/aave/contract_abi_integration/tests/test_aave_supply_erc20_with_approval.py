
import re
import time
import json
"""
Test for supplying an ERC20 token on Aave with approval step
"""
import os
import requests
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from ....base import process_result_and_simulate_tx, fetch_multistep_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID

from ..aave_supply_contract_workflow import AaveSupplyContractWorkflow

from utils import w3, Web3

from ...common import aave_revoke_usdc_approval

# Invoke this with python3 -m pytest -s -k "test_aave_supply_erc20_with_approval"
def test_contract_aave_supply_erc20_with_approval():
    token = "USDC"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    # Make sure to revoke any USDC pre-approval to ensure Aave UI is in the correct state to show approval flow
    aave_revoke_usdc_approval()
    # Step 1 - Approve supply of USDC
    multi_step_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # Assert what the user will see on the UI
    assert multi_step_result.description == "Approve supply of 0.1 USDC on Aave"

    # Simulating user signing/confirming a tx on the UI with their wallet
    tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multi_step_result)

    # Mocking FE response payload to backend
    curr_step_client_payload = {
        "id": multi_step_result.step_id,
        "type": multi_step_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    workflow_id = multi_step_result.workflow_id

    multi_step_workflow = fetch_multistep_workflow_from_db(workflow_id)

    # Step 2 - Process Step 1 response from FE and continue to Step 2 which is to confirm supply of USDC
    multi_step_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multi_step_workflow, curr_step_client_payload).run()

    assert multi_step_result.description == "Confirm supply of 0.1 USDC on Aave"

    assert multi_step_result.is_final_step

    tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multi_step_result)

    curr_step_client_payload = {
        "id": multi_step_result.step_id,
        "type": multi_step_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    multi_step_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multi_step_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multi_step_result.status == "terminated"

    # TODO - For thorough validation, ensure to assert the actual amount used in tx matches expectation by fetching decoded tx data from Tenderly