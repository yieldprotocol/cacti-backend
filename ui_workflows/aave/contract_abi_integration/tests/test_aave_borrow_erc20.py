from ....base import process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID
from ...common import aave_supply_eth_for_borrow_test
from ..aave_borrow_contract_workflow import AaveBorrowContractWorkflow

# Invoke this with python3 -m pytest -s -k "test_contract_aave_borrow_erc20"
def test_contract_aave_borrow_erc20(setup_fork):
    token = "DAI"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    # Pre-supply ETH to Aave to setup the test environment for borrow
    aave_supply_eth_for_borrow_test()

    multistep_result = AaveBorrowContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # Assert what the user will see on the UI
    assert multistep_result.description == "Confirm borrow of 0.1 DAI on Aave"

    assert multistep_result.is_final_step == True

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

    # Process FE response payload
    multistep_result = AaveBorrowContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multistep_result.status == "terminated"

    # TODO - For thorough validation, ensure to assert the actual amount used in tx matches expectation by fetching decoded tx data from Tenderly