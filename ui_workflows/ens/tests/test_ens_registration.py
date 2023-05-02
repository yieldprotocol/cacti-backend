import os
import traceback
import time
from ui_workflows.ens import ENSRegistrationWorkflow
from ui_workflows.base import MultiStepResult, setup_mock_db_objects, tenderly_simulate_tx
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)

# Invoke this with python3 -m ui_workflows.ens.tests.test_ens_registration 
if __name__ == "__main__":
    try:
        tenderly_api_access_key = os.environ.get("TENDERLY_API_ACCESS_KEY", None)
        epoch_seconds = int(time.time())
        domain_to_register = f"test{epoch_seconds}.eth"
        wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        wallet_chain_id = 1  # Tenderly Mainnet Fork
        workflow_type = "register-ens-domain"
        worfklow_params = {
            "domain": domain_to_register,
        }
        mock_db_objects = setup_mock_db_objects()
        mock_chat_message = mock_db_objects['mock_chat_message']
        mock_message_id = mock_chat_message.id

        print("Step 1: Request to register ENS domain...")

        multiStepResult: MultiStepResult = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, mock_message_id, workflow_type, worfklow_params, None, None).run()

        if multiStepResult.status != "success":
            raise Exception(multiStepResult)
        
        tenderly_simulate_tx(wallet_address, multiStepResult.tx)
        
        print("Step 2: Confirm registration")

        workflow_id = multiStepResult.workflow_id
        curr_step_client_payload = {
            "id": multiStepResult.step_id,
            "type": multiStepResult.step_type,
            "status": multiStepResult.status,
            "statusMessage": "TX successfully sent",
            "userActionData": "Sample TX HASH"
        }

        workflow = MultiStepWorkflow.query.filter(MultiStepWorkflow.id == workflow_id).first()

        multiStepResult: MultiStepResult = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, mock_message_id, workflow_type, worfklow_params, workflow, curr_step_client_payload).run()

        if multiStepResult.status != "success":
            raise Exception(multiStepResult)

        tenderly_simulate_tx(wallet_address, multiStepResult.tx)

        print("Final checks")

        curr_step_client_payload = {
            "id": multiStepResult.step_id,
            "type": multiStepResult.step_type,
            "status": multiStepResult.status,
            "statusMessage": "TX successfully sent",
            "userActionData": "Sample TX HASH"
        }   

        multiStepResult: MultiStepResult = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, mock_message_id, workflow_type, worfklow_params, workflow, curr_step_client_payload).run()
        
        print(multiStepResult)

        print("Domain registered successfully")
    except Exception as e:
        traceback.print_exc()
        print("Workflow failed")

