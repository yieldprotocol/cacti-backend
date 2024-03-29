
"""
Test for supplying an ETH amount greater than account balance on Aave
"""
import context
from ....base import setup_mock_db_objects, process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from ..aave_supply_contract_workflow import AaveSupplyContractWorkflow

# Invoke this with python3 -m pytest -s -k "test_contract_aave_supply_extreme_amount"
def test_contract_aave_supply_extreme_amount(setup_fork):
    web3_provider = context.get_web3_provider()
    current_eth_balance = web3_provider.eth.get_balance(TEST_WALLET_ADDRESS)
    test_extreme_eth_amount = current_eth_balance + 10*10**18 # Add 10 ETH to the current available balance

    token = "ETH"
    amount = test_extreme_eth_amount 
    workflow_params = {"token": token, "amount": amount}

    multistep_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # Assert what the user will see on the UI
    assert multistep_result.error_msg == "Insufficient ETH balance in wallet"