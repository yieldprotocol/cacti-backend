
import re
from logging import basicConfig, INFO
import time
import json
import uuid
import os
import requests
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from ....base import setup_mock_db_objects, process_result_and_simulate_tx, fetch_multistep_workflow_from_db

from ..aave_supply_ui_workflow import AaveSupplyUIWorkflow

# Invoke this with python3 -m ui_workflows.aave.ui_integration.tests.test_aave_supply
wallet_chain_id = 1  # Tenderly Mainnet Fork
wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
mock_chat_message_id = str(uuid.uuid4())
workflow_type = "aave-supply"
token = "LINK"
operation = "Supply"
amount = 0.1
workflow_params = {"token": token, "amount": amount}

mock_db_objects = setup_mock_db_objects()
mock_chat_message = mock_db_objects['mock_chat_message']
mock_message_id = mock_chat_message.id

multiStepResult = AaveSupplyUIWorkflow(wallet_chain_id, wallet_address, mock_chat_message_id, workflow_type, workflow_params).run()

process_result_and_simulate_tx(wallet_address, multiStepResult)

workflow_id = multiStepResult.workflow_id
curr_step_client_payload = {
    "id": multiStepResult.step_id,
    "type": multiStepResult.step_type,
    "status": multiStepResult.status,
    "statusMessage": "TX successfully sent",
    "userActionData": "Sample TX HASH"
}

multistep_workflow = fetch_multistep_workflow_from_db(workflow_id)

multiStepResult = AaveSupplyUIWorkflow(wallet_chain_id, wallet_address, mock_chat_message_id, workflow_type, workflow_params, multistep_workflow, curr_step_client_payload).run()

process_result_and_simulate_tx(wallet_address, multiStepResult)