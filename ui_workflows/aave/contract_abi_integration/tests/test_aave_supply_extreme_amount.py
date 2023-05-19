
"""
Test for supplying an ETH amount greater than account balance on Aave
"""
import re
from logging import basicConfig, INFO

from utils import w3
from ....base import setup_mock_db_objects, process_result_and_simulate_tx, fetch_multistep_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from ..aave_supply_contract_workflow import AaveSupplyContractWorkflow

# Invoke this with python3 -m ui_workflows.aave.contract_abi_integration.tests.test_aave_supply_extreme_amount
current_eth_balance = w3.eth.get_balance(TEST_WALLET_ADDRESS)
test_extreme_eth_amount = current_eth_balance + 10*10**18 # Add 10 ETH to the current available balance

token = "ETH"
amount = test_extreme_eth_amount
workflow_params = {"token": token, "amount": amount}

multistep_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

# Assert what the user will see on the UI
assert multistep_result.error_msg == "Insufficient ETH balance in wallet"

# TODO: Figure out how to run the tests in isolation with their own snapshot of the fork state so that they don't interfere with each other
