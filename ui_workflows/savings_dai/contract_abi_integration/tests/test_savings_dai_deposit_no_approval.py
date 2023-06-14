"""
Test for depositing DAI on SavingsDAI without approval step as it is already pre-approved
"""
import context
from utils import get_token_balance, parse_token_amount
from ....base import process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from ...common import  savings_dai_set_dai_allowance
from ..savings_dai_deposit_contract_workflow import SavingsDaiDepositContractWorkflow

# Invoke this with python3 -m pytest -s -k "test_contract_savings_dai_deposit_no_approval"
def test_contract_savings_dai_deposit_no_approval(setup_fork):
    token = "DAI"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    dai_balance_start = get_token_balance(context.get_web3_provider(), TEST_WALLET_CHAIN_ID, token, TEST_WALLET_ADDRESS)

    # Set allowance for pre-approval
    savings_dai_set_dai_allowance(int(amount * 10 ** 18))

    # Confirm deposit of DAI with no approval step
    multistep_result = SavingsDaiDepositContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    assert multistep_result.description == "Confirm deposit of 0.1 DAI on SavingsDAI"

    assert multistep_result.is_final_step

    tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multistep_result)

    curr_step_client_payload = {
        "id": multistep_result.step_id,
        "type": multistep_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    workflow_id = multistep_result.workflow_id

    multistep_workflow = fetch_multi_step_workflow_from_db(workflow_id)

    multistep_result = SavingsDaiDepositContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multistep_result.status == "terminated"

    dai_balance_end = get_token_balance(context.get_web3_provider(), TEST_WALLET_CHAIN_ID, token, TEST_WALLET_ADDRESS)

    assert dai_balance_end == dai_balance_start - parse_token_amount(TEST_WALLET_CHAIN_ID, token, amount)