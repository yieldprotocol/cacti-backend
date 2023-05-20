
"""
Test for validating that workflow should return an error if token not found in user's profile
"""
from ....base import MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from ..aave_supply_ui_workflow import AaveSupplyUIWorkflow

# Invoke this with python3 -m pytest -s -k "test_ui_aave_supply_no_token_error"
def test_ui_aave_supply_no_token_error(setup_fork):
    fork_id = setup_fork['fork_id']
    token = "XXYYZZ"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    # Step 1 - Try to initiate approval
    multi_step_result = AaveSupplyUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, fork_id=fork_id).run()

    assert multi_step_result.status == "error"
    assert multi_step_result.error_msg == "Token XXYYZZ not found on user's profile"
