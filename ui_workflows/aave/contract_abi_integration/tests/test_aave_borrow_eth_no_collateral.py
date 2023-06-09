
"""
Test for borrowing ETH on Aave 

"""
from ....base import process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID
from ...common import aave_supply_eth_for_borrow_test, aave_set_eth_approval
from ..aave_borrow_contract_workflow import AaveBorrowContractWorkflow

# Invoke this with python3 -m pytest -s -k "test_contract_aave_borrow_eth_no_collateral"
def test_contract_aave_borrow_eth_no_collateral(setup_fork):
    token = "ETH"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    # Pre-approve ETH borrow to set the test environment for borrow
    aave_set_eth_approval(1*10**18)

    multistep_result = AaveBorrowContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # TODO: This will fail as Tenderly is not able to simulate the tx on the latest block for a fork, investigate why
    assert multistep_result.status == 'error'
    assert multistep_result.error_msg == 'The collateral balance is 0'


   