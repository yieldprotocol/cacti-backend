import os
import traceback
import time
from ui_workflows.ens import ENSRegistrationWorkflow
from ui_workflows.base import MultiStepResult, setup_mock_db_objects, process_result_and_simulate_tx, fetch_multistep_workflow_from_db
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)

# Invoke this with python -m pytest -s -k "test_ens_registration"
def test_ens_registration():
    tenderly_api_access_key = os.environ.get("TENDERLY_API_ACCESS_KEY", None)
    epoch_seconds = int(time.time())
    domain_to_register = f"test{epoch_seconds}.eth"
    wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    worfklow_params = {
        "domain": domain_to_register,
    }
    mock_db_objects = setup_mock_db_objects()
    mock_chat_message = mock_db_objects['mock_chat_message']
    mock_message_id = mock_chat_message.id

    print("Step 1: Request to register ENS domain...")

    multiStepResult: MultiStepResult = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, mock_message_id, worfklow_params, None, None).run()

    process_result_and_simulate_tx(wallet_address, multiStepResult)
    
    print("Step 2: Confirm registration")

    workflow_id = multiStepResult.workflow_id
    curr_step_client_payload = {
        "id": multiStepResult.step_id,
        "type": multiStepResult.step_type,
        "status": multiStepResult.status,
        "statusMessage": "TX successfully sent",
        "userActionData": "Sample TX HASH"
    }

    multistep_workflow = fetch_multistep_workflow_from_db(workflow_id)

    multiStepResult: MultiStepResult = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, mock_message_id, worfklow_params, multistep_workflow, curr_step_client_payload).run()

    process_result_and_simulate_tx(wallet_address, multiStepResult)

    print("Final checks")

    curr_step_client_payload = {
        "id": multiStepResult.step_id,
        "type": multiStepResult.step_type,
        "status": multiStepResult.status,
        "statusMessage": "TX successfully sent",
        "userActionData": "Sample TX HASH"
    }   

    multiStepResult: MultiStepResult = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, mock_message_id, worfklow_params, multistep_workflow, curr_step_client_payload).run()
    
    process_result_and_simulate_tx(wallet_address, multiStepResult)

    print("Domain registered successfully")


