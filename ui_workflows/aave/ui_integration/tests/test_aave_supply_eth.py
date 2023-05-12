
"""
Test for supplying a ETH into Aave
"""
import re
from logging import basicConfig, INFO

from ....base import setup_mock_db_objects, process_result_and_simulate_tx, fetch_multistep_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID

from ..aave_supply_ui_workflow import AaveSupplyUIWorkflow

# Invoke this with python3 -m ui_workflows.aave.ui_integration.tests.test_aave_supply
workflow_type = "aave-supply"
token = "ETH"
amount = 0.1
workflow_params = {"token": token, "amount": amount}

multistep_result = AaveSupplyUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params).run()

# Assert what the user will see on the UI
assert multistep_result.description == "Confirm supply of 0.1 ETH into Aave"

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

# Process FE response payload
multistep_result = AaveSupplyUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params, multistep_workflow, curr_step_client_payload).run()

# Final state of workflow should be terminated
assert multistep_result.status == "terminated"

# TODO - For thorough validation, ensure to assert the actual amount used in tx matches expectation by fetching decoded tx data from Tenderly