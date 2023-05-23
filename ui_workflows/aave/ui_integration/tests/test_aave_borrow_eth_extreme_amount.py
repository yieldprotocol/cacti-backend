
"""
Test for borrowing exteme amount of ETH on Aave which requires the user to perform special acknowledgement due to liquidation risk
"""
import re
from ....base import process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID
from ...common import aave_supply_eth_for_borrow_test
from ..aave_borrow_ui_workflow import AaveBorrowUIWorkflow

# Invoke this with python3 -m pytest -s -k "test_ui_aave_eth_borrow_extreme_amount"
def test_ui_aave_eth_borrow_extreme_amount(setup_fork):
    token = "ETH"
    amount = 100
    workflow_params = {"token": token, "amount": amount}

    # Pre-supply ETH to Aave to setup the test environment for borrow
    aave_supply_eth_for_borrow_test()

    # Step 1 - Check liquidation risk
    multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    assert multistep_result.step_type == "check_ETH_liquidation_risk"

    # Assert what the user will see on the UI
    regex = re.compile(r'Acknowledge liquidation risk due to high borrow amount of 0.800.* ETH on Aave')
    assert bool(regex.fullmatch(multistep_result.description))
    # Assert user action type
    assert multistep_result.user_action_type == "acknowledge"

    # Mocking FE response payload to backend
    curr_step_client_payload = {
        "id": multistep_result.step_id,
        "type": multistep_result.step_type,
        "status": 'success',
        "statusMessage": "Acknowledged liquidation risk",
        "userActionData": "accepted"
    }

    workflow_id = multistep_result.workflow_id

    multistep_workflow = fetch_multi_step_workflow_from_db(workflow_id)

    # Step 2 - Initiate approval after user acknowledges liquidation risk
    multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    # Check to ensure the amount displayed on the UI is not the same as the user amount as the user borrow amount is too large and should be overriden by the Aave UI
    pattern = r'\d+(\.\d+)?'
    match = re.search(pattern, multistep_result.description)
    display_eth_amount = float(match.group())    
    assert display_eth_amount != amount

    assert multistep_result.step_type == "initiate_ETH_approval"

    assert multistep_result.user_action_type == "tx"

    tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multistep_result)

    # Mocking FE response payload to backend
    curr_step_client_payload = {
        "id": multistep_result.step_id,
        "type": multistep_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    # Step 3 - Confirm borrow
    multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    assert multistep_result.step_type == "confirm_ETH_borrow"

    assert multistep_result.is_final_step

    # Mocking FE response payload to backend
    curr_step_client_payload = {
        "id": multistep_result.step_id,
        "type": multistep_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    assert multistep_result.is_final_step

    # Final state of workflow should be terminated
    assert multistep_result.status == "terminated"

    # TODO - For thorough validation, figure out how to fetch decoded tx data from Tenderly and assert the amount processed
