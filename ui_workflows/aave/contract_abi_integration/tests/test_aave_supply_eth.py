
"""
Test for supplying a ETH on Aave
"""
import re

from ....base import setup_mock_db_objects, process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from ...contract_abi_integration import AaveSupplyContractWorkflow

# Invoke this with python3 -m pytest -s -k "test_contract_aave_supply_eth"
def test_contract_aave_supply_eth(setup_fork):
    token = "ETH"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    multi_step_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    assert multi_step_result.description == "Confirm supply of 0.1 ETH on Aave"

    assert multi_step_result.is_final_step

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

    # Process FE response payload
    multi_step_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multi_step_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multi_step_result.status == "terminated"

    # TODO - For thorough validation, ensure to assert the actual amount used in tx matches expectation by fetching decoded tx data from Tenderly