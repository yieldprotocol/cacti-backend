
"""
Test for borrowing ETH on Aave 
"""
from ....base import process_result_and_simulate_tx, fetch_multistep_workflow_from_db, TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID
from ..aave_borrow_ui_workflow import AaveBorrowUIWorkflow

# Invoke this with python3 -m pytest -s -k "test_ui_aave_borrow_eth"
def test_ui_aave_borrow_eth():
    token = "ETH"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # Assert what the user will see on the UI
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

    multistep_workflow = fetch_multistep_workflow_from_db(workflow_id)

    # Process FE response payload
    multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multistep_result.status == "terminated"

    # TODO - For thorough validation, ensure to assert the actual amount used in tx matches expectation by fetching decoded tx data from Tenderly