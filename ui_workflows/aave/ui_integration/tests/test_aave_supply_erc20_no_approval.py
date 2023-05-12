"""
Test for supplying an ERC20 token into Aave without approval step as it is already pre-approved
"""
from logging import basicConfig, INFO
from dataclasses import dataclass, asdict

from ....base import process_result_and_simulate_tx, fetch_multistep_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from ..aave_supply_ui_workflow import AaveSupplyUIWorkflow
from ..common import  aave_set_usdc_allowance

# Invoke this with python3 -m ui_workflows.aave.ui_integration.tests.test_aave_supply_erc20_no_approval
workflow_type = "aave-supply"
token = "USDC"
amount = 0.1
workflow_params = {"token": token, "amount": amount}

# Set allowance for pre-approval
aave_set_usdc_allowance(int(amount * 10 ** 6))

# Confirm supply of USDC with no approval step
multistep_result = AaveSupplyUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params).run()

assert multistep_result.description == "Confirm supply of 0.1 USDC into Aave"

assert multistep_result.is_final_step

tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multistep_result)

curr_step_client_payload = {
    "id": multistep_result.step_id,
    "type": multistep_result.step_type,
    "status": 'success',
    "statusMessage": "TX successfully sent",
    "userActionData": tx_hash
}

workflow_id = multistep_result.workflow_id

multistep_workflow = fetch_multistep_workflow_from_db(workflow_id)

multistep_result = AaveSupplyUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params, multistep_workflow, curr_step_client_payload).run()

# Final state of workflow should be terminated
assert multistep_result.status == "terminated"

# TODO - For thorough validation, ensure to assert the actual amount used in tx matches expectation by fetching decoded tx data from Tenderly