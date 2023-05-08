import os
from ui_workflows.compound import CompoundWithdrawWorkflow
from ui_workflows.base import MultiStepResult, setup_mock_db_objects, tenderly_simulate_tx
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)

# Invoke this with python3 -m ui_workflows.compound.tests.test_compound_withdraw
if __name__ == "__main__":
    tenderly_api_access_key = os.environ.get("TENDERLY_API_ACCESS_KEY", None)
    token_to_withdraw = "TUSD"
    amount_to_withdraw = 0.0001
    wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    workflow_type = "withdraw-token-on-compound"
    worfklow_params = {
        "token": token_to_withdraw,
        "amount": amount_to_withdraw,
    }
    mock_db_objects = setup_mock_db_objects()
    mock_chat_message = mock_db_objects['mock_chat_message']
    mock_message_id = mock_chat_message.id

    print(f"Step 1: Confirm Withdraw of {token_to_withdraw}")

    multiStepResult: MultiStepResult = CompoundWithdrawWorkflow(wallet_chain_id, wallet_address, mock_message_id, workflow_type, worfklow_params, None, None).run()
    
    tenderly_simulate_tx(wallet_address, multiStepResult.tx)
    
    print(multiStepResult)

    print(f"Successfully Withdrawn {worfklow_params['token']} {worfklow_params['amount']}")
