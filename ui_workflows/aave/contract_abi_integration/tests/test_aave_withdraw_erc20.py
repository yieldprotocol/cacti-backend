
import context
from utils import get_token_balance, parse_token_amount
from ....base import process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID
from ...common import aave_set_usdc_allowance
from ..aave_withdraw_contract_workflow import AaveWithdrawContractWorkflow
from ..aave_supply_contract_workflow import AaveSupplyContractWorkflow

# Invoke this with python3 -m pytest -s -k "test_contract_aave_withdraw_erc20"
def test_contract_aave_withdraw_erc20(setup_fork):
    token = "USDC"
    amount = 100
    workflow_params = {"token": token, "amount": amount}

    # Pre-deposit USDC in order to test withdraw
    aave_set_usdc_allowance(parse_token_amount(TEST_WALLET_CHAIN_ID, token, amount))
    multistep_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()
    tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multistep_result)

    usdc_balance_start = get_token_balance(context.get_web3_provider(), TEST_WALLET_CHAIN_ID, token, TEST_WALLET_ADDRESS)

    multistep_result = AaveWithdrawContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    # Assert what the user will see on the UI
    assert multistep_result.description == "Confirm withdraw of 100 USDC on Aave"

    assert multistep_result.is_final_step == True

    # Simulating user signing/confirming a tx on the UI with their wallet
    tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multistep_result)

    # Mocking FE response payload to backend
    curr_step_client_payload = {
        "id": multistep_result.step_id,
        "type": multistep_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    workflow_id = multistep_result.workflow_id

    multistep_workflow = fetch_multi_step_workflow_from_db(workflow_id)

    # Process FE response payload
    multistep_result = AaveWithdrawContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multistep_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multistep_result.status == "terminated"

    usdc_balance_end = get_token_balance(context.get_web3_provider(), TEST_WALLET_CHAIN_ID, token, TEST_WALLET_ADDRESS)
    assert usdc_balance_end == usdc_balance_start + parse_token_amount(TEST_WALLET_CHAIN_ID, token, amount)
