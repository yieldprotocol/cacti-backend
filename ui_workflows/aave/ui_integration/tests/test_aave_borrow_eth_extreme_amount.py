
"""
Test for borrowing exteme amount of ETH on Aave which requires the user to perform special acknowledgement due to liquidation risk
"""
import re
from ....base import process_result_and_simulate_tx, fetch_multistep_workflow_from_db, TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID
from ..aave_borrow_ui_workflow import AaveBorrowUIWorkflow

# Invoke this with python3 -m pytest -k "test_ui_aave_borrow_eth_extreme_amount"
def test_ui_aave_eth_borrow_extreme_amount():
    token = "ETH"
    amount = 100
    workflow_params = {"token": token, "amount": amount}

    # Step 1 - Check liquidation risk
    multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # Assert what the user will see on the UI
    regex = re.compile(r'Acknowledge liquidation risk due to high borrow amount of .* ETH on Aave')
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

    multistep_workflow = fetch_multistep_workflow_from_db(workflow_id)

    # Step 2 - Confirm borrow after user acknowledges liquidation risk
    multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    # Check to ensure the amount displayed on the UI is not the same as the user amount as the user borrow amount is too large and should be overriden by the Aave UI
    pattern = r'\d+(\.\d+)?'
    match = re.search(pattern, multistep_result.description)
    display_eth_amount = float(match.group())    
    assert display_eth_amount != amount

    assert multistep_result.user_action_type == "tx"

    assert multistep_result.is_final_step

    tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multistep_result)

    # Mocking FE response payload to backend
    curr_step_client_payload = {
        "id": multistep_result.step_id,
        "type": multistep_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    multistep_result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multistep_result.status == "terminated"

    # TODO - For thorough validation, ensure to assert the actual amount used in tx matches expectation by fetching decoded tx data from Tenderly