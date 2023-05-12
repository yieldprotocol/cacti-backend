
import re
from logging import basicConfig, INFO
import time
import json
import uuid
import os
import requests
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from ....base import process_result_and_simulate_tx, fetch_multistep_workflow_from_db, MOCK_CHAT_MESSAGE_ID, TEST_WALLET_ADDRESS, TEST_WALLET_CHAIN_ID

from ..aave_supply_ui_workflow import AaveSupplyUIWorkflow

# Invoke this with python3 -m ui_workflows.aave.ui_integration.tests.test_aave_supply
workflow_type = "aave-supply"
token = "USDC"
amount = 0.1
workflow_params = {"token": token, "amount": amount}


multiStepResult = AaveSupplyUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params).run()

process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multiStepResult)

workflow_id = multiStepResult.workflow_id
curr_step_client_payload = {
    "id": multiStepResult.step_id,
    "type": multiStepResult.step_type,
    "status": multiStepResult.status,
    "statusMessage": "TX successfully sent",
    "userActionData": "Sample TX HASH"
}

multistep_workflow = fetch_multistep_workflow_from_db(workflow_id)

multiStepResult = AaveSupplyUIWorkflow(TEST_WALLET_CHAIN_ID, TEST_WALLET_ADDRESS, MOCK_CHAT_MESSAGE_ID, workflow_type, workflow_params, multistep_workflow, curr_step_client_payload).run()

process_result_and_simulate_tx(TEST_WALLET_ADDRESS, multiStepResult)