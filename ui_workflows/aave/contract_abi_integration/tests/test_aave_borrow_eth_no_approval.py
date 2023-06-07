
"""
Test for borrowing ETH on Aave 
"""
from ....base import process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID
from ...common import aave_supply_eth_for_borrow_test, aave_set_eth_approval
from ..aave_borrow_contract_workflow import AaveBorrowContractWorkflow

# Invoke this with python3 -m pytest -s -k "test_contract_aave_borrow_eth_no_approval"
def test_contract_aave_borrow_eth_no_approval(setup_fork):
    token = "ETH"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    # Pre-supply ETH to Aave to setup the test environment for borrow
    aave_supply_eth_for_borrow_test()

    # Pre-approve ETH borrow to set the test environment for borrow
    aave_set_eth_approval(1*10**18)

    multistep_result = AaveBorrowContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    assert multistep_result.description == "Confirm borrow of 0.1 ETH on Aave"

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

    multistep_workflow = fetch_multi_step_workflow_from_db(workflow_id)

    curr_step_client_payload = {
        "id": multistep_result.step_id,
        "type": multistep_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    multistep_result = AaveBorrowContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multistep_result.status == "terminated"

    # TODO - For thorough validation, figure out how to fetch decoded tx data from Tenderly and assert the amount processed
