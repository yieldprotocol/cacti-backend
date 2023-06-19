
"""
Test for supplying a ETH on Aave
"""
import context
from utils import get_token_balance, parse_token_amount
from ....base import process_result_and_simulate_tx, fetch_multi_step_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID
from ...contract_abi_integration import AaveSupplyContractWorkflow

# Invoke this with python3 -m pytest -s -k "test_contract_aave_supply_eth"
def test_contract_aave_supply_eth(setup_fork):
    token = "ETH"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    eth_balance_start = get_token_balance(context.get_web3_provider(), TEST_WALLET_CHAIN_ID, token, TEST_WALLET_ADDRESS)

    multi_step_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params).run()

    assert multi_step_result.description == "Confirm supply of 0.1 ETH on Aave"

    assert multi_step_result.is_final_step

    # Simulating user signing/confirming a tx on the UI with their wallet
    tx_hash = process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multi_step_result)

    # Mocking FE response payload to backend
    curr_step_client_payload = {
        "id": multi_step_result.step_id,
        "type": multi_step_result.step_type,
        "status": 'success',
        "statusMessage": "TX successfully sent",
        "userActionData": tx_hash
    }

    workflow_id = multi_step_result.workflow_id

    multi_step_workflow = fetch_multi_step_workflow_from_db(workflow_id)

    # Process FE response payload
    multi_step_result = AaveSupplyContractWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_params, multi_step_workflow, curr_step_client_payload).run()

    # Final state of workflow should be terminated
    assert multi_step_result.status == "terminated"

    eth_balance_end = get_token_balance(context.get_web3_provider(), TEST_WALLET_CHAIN_ID, token, TEST_WALLET_ADDRESS)
    assert eth_balance_end == eth_balance_start - parse_token_amount(TEST_WALLET_CHAIN_ID, token, amount)
