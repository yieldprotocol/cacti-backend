"""
Test for depositing Dai on SavingsDai with approval step
"""
import context
from utils import get_token_balance, parse_token_amount
import os
import requests
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from ....base import process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID

from ..savings_dai_deposit_contract_workflow import SavingsDaiDepositContractWorkflow

from ...common import savings_dai_revoke_dai_approval

# Invoke this with python3 -m pytest -s -k "test_contract_savings_dai_deposit_with_approval"
def test_contract_savings_dai_deposit_with_approval(setup_fork):
    token = "DAI"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    dai_balance_start = get_token_balance(context.get_web3_provider(), TEST_WALLET_CHAIN_ID, token, TEST_WALLET_ADDRESS)

    # Make sure to revoke any DAI pre-approval to ensure SavingsDai UI is in the correct state to show approval flow
    savings_dai_revoke_dai_approval()
    
    # Step 1 - Approve deposit of DAI
    multi_step_result = SavingsDaiDepositContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # Assert what the user will see on the UI
    assert multi_step_result.description == "Approve deposit of 0.1 DAI on SavingsDai"

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

    multi_step_workflow = fetch_multi_step_workflow_from_db(workflow_id)

    # Step 2 - Process Step 1 response from FE and continue to Step 2 which is to confirm deposit of DAI
    multi_step_result = SavingsDaiDepositContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multi_step_workflow, curr_step_client_payload).run()

    assert multi_step_result.description == "Confirm deposit of 0.1 DAI on SavingsDai"

    assert multi_step_result.is_final_step

    tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multi_step_result)

    curr_step_client_payload = {
        "id": multi_step_result.step_id,
        "type": multi_step_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    multi_step_result = SavingsDaiDepositContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multi_step_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multi_step_result.status == "terminated"

    dai_balance_end = get_token_balance(context.get_web3_provider(), TEST_WALLET_CHAIN_ID, token, TEST_WALLET_ADDRESS)
    assert dai_balance_end == dai_balance_start - parse_token_amount(TEST_WALLET_CHAIN_ID, token, amount)