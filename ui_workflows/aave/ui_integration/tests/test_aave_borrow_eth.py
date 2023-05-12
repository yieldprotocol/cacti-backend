
import uuid

from ....base import process_result_and_simulate_tx, TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID
from ..aave_borrow_ui_workflow import AaveBorrowUIWorkflow

# Invoke this with python3 -m ui_workflows.__aave.ui_integration.aave_eth_supply_single_step_demo
workflow_type = "aave-borrow"
token = "USDC"
amount = 0.1
workflow_params = {"token": token, "amount": amount}

result = AaveBorrowUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params).run()

process_result_and_simulate_tx(TEST_WALLET_ADDRESS, result)

    