import os
import traceback
import time
from ui_workflows.ens import ENSRegistrationContractWorkflow
from ui_workflows.base import MultiStepResult, setup_mock_db_objects, process_result_and_simulate_tx, fetch_multi_step_workflow_from_db

# Invoke this with python -m pytest -s -k "test_contract_ens_registration"
def test_contract_ens_registration(setup_fork):
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

    multi_step_result: MultiStepResult = ENSRegistrationContractWorkflow(wallet_chain_id, wallet_address, mock_message_id, worfklow_params, None, None).run()

    process_result_and_simulate_tx(wallet_address, multi_step_result)

    print("Step 2: Confirm registration")

    workflow_id = multi_step_result.workflow_id
    curr_step_client_payload = {
        "id": multi_step_result.step_id,
        "type": multi_step_result.step_type,
        "status": multi_step_result.status,
        "statusMessage": "TX successfully sent",
        "userActionData": "Sample TX HASH"
    }

    multi_step_workflow = fetch_multi_step_workflow_from_db(workflow_id)

    multi_step_result: MultiStepResult = ENSRegistrationContractWorkflow(wallet_chain_id, wallet_address, mock_message_id, worfklow_params, multi_step_workflow, curr_step_client_payload).run()

    process_result_and_simulate_tx(wallet_address, multi_step_result)

    print("Final checks")

    curr_step_client_payload = {
        "id": multi_step_result.step_id,
        "type": multi_step_result.step_type,
        "status": multi_step_result.status,
        "statusMessage": "TX successfully sent",
        "userActionData": "Sample TX HASH"
    }   

    multi_step_result: MultiStepResult = ENSRegistrationContractWorkflow(wallet_chain_id, wallet_address, mock_message_id, worfklow_params, multi_step_workflow, curr_step_client_payload).run()

    assert multi_step_result.status == "terminated"
    
    print("Domain registered successfully")


