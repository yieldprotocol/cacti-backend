
"""
Test for supplying a ETH on Lido
"""

from ...base import MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from .. import LidoTextWorkflow

# Invoke this with python3 -m pytest -s -k "test_lido_deposit"
def test_lido_deposit(setup_fork):
    amount = 1
    workflow_params = {"amount": amount}

    multi_step_result = LidoTextWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, LidoTextWorkflow.WORKFLOW_TYPE ,workflow_params).run()
    assert multi_step_result.description == "Deposit 1 ETH to Lido"