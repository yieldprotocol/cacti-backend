
"""
Test for supplying an ETH amount greater than account balance on Aave
"""
import re

import context
from ....base import MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from ..aave_supply_ui_workflow import AaveSupplyUIWorkflow

# Invoke this with python3 -m pytest -s -k "test_ui_ave_supply_extreme_amount"
def test_ui_ave_supply_extreme_amount(setup_fork):
    web3_provider = context.get_web3_provider()
    current_eth_balance = web3_provider.eth.get_balance(TEST_WALLET_ADDRESS)
    test_extreme_eth_amount = current_eth_balance + 10*10**18 # Add 10 ETH to the current available balance

    token = "ETH"
    amount = test_extreme_eth_amount
    workflow_params = {"token": token, "amount": amount}

    multi_step_result = AaveSupplyUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # Assert what the user will see on the UI
    regex = re.compile(r'Confirm supply of 4,699.871.* ETH on Aave')
    assert bool(regex.fullmatch(multi_step_result.description))
