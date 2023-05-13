
"""
Test for borrowing ETH on Aave with approval step (https://docs.aave.com/developers/tokens/debttoken#approvedelegation)
"""
import json
from utils import w3, Web3
from ....base import process_result_and_simulate_tx, fetch_multistep_workflow_from_db, TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID
from ..aave_borrow_ui_workflow import AaveBorrowUIWorkflow
from ..common import aave_revoke_eth_approval

# Invoke this with python3 -m ui_workflows.aave.ui_integration.tests.test_aave_borrow_eth_with_approval
workflow_type = "aave-borrow"
token = "ETH"
amount = 0.01
workflow_params = {"token": token, "amount": amount}

# Revoke ETH pre-approval if any to ensure we start from a clean state
aave_revoke_eth_approval()

# Step 1 - Initiate approval
multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params).run()

# Assert what the user will see on the UI
assert multistep_result.description == "Approve borrow of 0.01 ETH on Aave"

# Simulating user signing/confirming a tx on the UI with their wallet
tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multistep_result)

# Mocking FE response payload to backend
curr_step_client_payload = {
    "id": multistep_result.step_id,
    "type": multistep_result.step_type,
    "status": 'success',
    "statusMessage": "TX successfully sent",
    "userActionData": tx_hash
}

workflow_id = multistep_result.workflow_id

multistep_workflow = fetch_multistep_workflow_from_db(workflow_id)

# Step 2 - Confirm borrow after user approves borrow
multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params, multistep_workflow, curr_step_client_payload).run()

assert multistep_result.description == "Confirm borrow of 0.01 ETH on Aave"

# Simulating user signing/confirming a tx on the UI with their wallet
tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multistep_result)

# Mocking FE response payload to backend
curr_step_client_payload = {
    "id": multistep_result.step_id,
    "type": multistep_result.step_type,
    "status": 'success',
    "statusMessage": "TX successfully sent",
    "userActionData": tx_hash
}

multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params, multistep_workflow, curr_step_client_payload).run()

# Final state of workflow should be terminated
assert multistep_result.status == "terminated"

# TODO - For thorough validation, ensure to assert the actual amount used in tx matches expectation by fetching decoded tx data from Tenderly