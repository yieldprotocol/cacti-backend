import os
import uuid
from ui_workflows.ens import ENSSetTextWorkflow
from ui_workflows.base import process_result_and_simulate_tx

# Invoke this with python3 -m ui_workflows.ens.tests.test_ens_set_text
if __name__ == "__main__":
    domain = "owocki.gitcoin.eth"
    wallet_address = "0xDDF369C3bf18b1B12EA295d597B943b955eF4671"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    mock_chat_message_id = str(uuid.uuid4())
    workflow_params = {"domain": domain, "key":"url", "value":"http://example.net"}

    result = ENSSetTextWorkflow(wallet_chain_id, wallet_address, mock_chat_message_id, workflow_params).run()

    process_result_and_simulate_tx(wallet_address, result)