import os
from ui_workflows.compound import CompoundSupplyWorkflow
from ui_workflows.base import MultiStepResult, setup_mock_db_objects, tenderly_simulate_tx
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)

# Invoke this with python3 -m ui_workflows.compound.tests.test_compound_supply
if __name__ == "__main__":
    tenderly_api_access_key = os.environ.get("TENDERLY_API_ACCESS_KEY", None)
    token_to_supply = "TUSD"
    amount_to_supply = 0.0001
    wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    workflow_type = "supply-token-on-compound"
    worfklow_params = {
        "token": token_to_supply,
        "amount": amount_to_supply,
    }
    mock_db_objects = setup_mock_db_objects()
    mock_chat_message = mock_db_objects['mock_chat_message']
    mock_message_id = mock_chat_message.id

    print(f"Step 1: Enable Supply of {token_to_supply}")

    multiStepResult: MultiStepResult = CompoundSupplyWorkflow(wallet_chain_id, wallet_address, mock_message_id, workflow_type, worfklow_params, None, None).run()
    
    # if already enabled no transaction so tx = None
    if multiStepResult.tx!=None: tenderly_simulate_tx(wallet_address, multiStepResult.tx)
    
    print(f"Step 2: Confirm Supply of {token_to_supply}")

    workflow_id = multiStepResult.workflow_id
    curr_step_client_payload = {
        "id": multiStepResult.step_id,
        "type": multiStepResult.step_type,
        "status": multiStepResult.status,
        "statusMessage": "TX successfully sent",
        "userActionData": "Sample TX HASH"
    }

    workflow = MultiStepWorkflow.query.filter(MultiStepWorkflow.id == workflow_id).first()

    multiStepResult: MultiStepResult = CompoundSupplyWorkflow(wallet_chain_id, wallet_address, mock_message_id, workflow_type, worfklow_params, workflow, curr_step_client_payload).run()

    # # TODO: Note: This will error out as for some reason Tenderly doesn't preserve chain state across transactions for simulation API. Manually executing txs via Metamak works fine. More invastigation needed.
    tenderly_simulate_tx(wallet_address, multiStepResult.tx)

    print("Final checks")

    curr_step_client_payload = {
        "id": multiStepResult.step_id,
        "type": multiStepResult.step_type,
        "status": multiStepResult.status,
        "statusMessage": "TX successfully sent",
        "userActionData": "Sample TX HASH"
    }   

    multiStepResult: MultiStepResult = CompoundSupplyWorkflow(wallet_chain_id, wallet_address, mock_message_id, workflow_type, worfklow_params, workflow, curr_step_client_payload).run()
    
    print(multiStepResult)

    print(f"Successfully Supplied {worfklow_params['token']} {worfklow_params['amount']}")
