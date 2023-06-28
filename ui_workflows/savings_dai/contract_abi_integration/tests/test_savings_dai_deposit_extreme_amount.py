
"""
Test for depositing a DAI amount greater than account balance on SavingsDai
"""
import context
from ....base import setup_mock_db_objects, process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from ..savings_dai_deposit_contract_workflow import SavingsDaiDepositContractWorkflow

# Invoke this with python3 -m pytest -s -k "test_contract_savings_dai_deposit_extreme_amount"
def test_contract_savings_dai_deposit_extreme_amount(setup_fork):
    web3_provider = context.get_web3_provider()
    current_dai_balance = web3_provider.dai.get_balance(TEST_WALLET_ADDRESS)
    test_extreme_dai_amount = current_dai_balance + 10*10**18 # Add 10 dai to the current available balance

    token = "DAI"
    amount = test_extreme_dai_amount 
    workflow_params = {"token": token, "amount": amount}

    multistep_result = SavingsDaiDepositContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # Assert what the user will see on the UI
    assert multistep_result.error_msg == "Insufficient dai balance in wallet"