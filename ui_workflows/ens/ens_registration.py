import re
from logging import basicConfig, INFO
import time
import json
import uuid
import os
import requests
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict
from dataclasses import dataclass, asdict

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import env
from utils import TENDERLY_FORK_URL, w3
from ..base import BaseUIWorkflow, MultiStepResult, BaseMultiStepWorkflow, WorkflowStepClientPayload, StepProcessingResult, tenderly_simulate_tx, setup_mock_db_objects
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)

TWO_MINUTES = 120000
TEN_SECONDS = 10000

class ENSRegistrationWorkflow(BaseMultiStepWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict, workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.ens_domain = workflow_params['domain']
        rpc_urls_to_intercept = ["https://web3.ens.domains/v1/mainnet"]
        total_steps = 2
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, workflow_type, workflow, workflow_params, curr_step_client_payload, rpc_urls_to_intercept, total_steps)


    def _handle_rpc_node_reqs(self, route):
        """Override to intercept requests to ENS API and modify response to simulate block production"""

        # eth_getBlockByNumber
        post_body = route.request.post_data
        
        # Interepting below request to modify timestamp to be 5 minutes in the future to simulate block production and allow ENS web app to not be stuck in waiting loop
        if "eth_getBlockByNumber" in post_body:
            curr_time_hex = hex(int(time.time()) + 300)
            data = requests.post(TENDERLY_FORK_URL, data=post_body)
            json_dict = data.json()
            json_dict["result"]["timestamp"] = curr_time_hex
            data = json_dict
            res_text = json.dumps(data)
            route.fulfill(body=res_text, headers={"access-control-allow-origin": "*", "access-control-allow-methods": "*", "access-control-allow-headers": "*"})
        else:
            super()._handle_rpc_node_reqs(route)

    def _goto_page_and_setup_walletconnect(self, page):
        """Override to go to ENS app and setup WalletConnect"""

        page.goto(f"https://app.ens.domains/name/{self.ens_domain}/register")

        # Search for WalletConnect and open QRCode modal
        page.get_by_text("Connect", exact=True).click()
        page.get_by_text("WalletConnect", exact=True).click()
        self._connect_to_walletconnect_modal(page)


    def _initialize_workflow_for_first_step(self, page, context) -> StepProcessingResult:
        """Initialize workflow and create first step"""

        description = f"ENS domain {self.ens_domain} request registration"

        # Create first step to request registration
        self._create_new_curr_step("request_register", 1, WorkflowStepUserActionType.tx, description)

        # Check for failure cases early so check if domain is already registered
        try:
            page.get_by_text("already register").wait_for()
            return StepProcessingResult(status='error', error_msg="Domain is already registered")
        except PlaywrightTimeoutError:
            # Domain is not registered
            pass

        # Find and click request registration button
        selector = '[data-testid="request-register-button"][type="primary"]'
        page.wait_for_selector(selector, timeout=TWO_MINUTES)
        page.click(selector)

        # Get browser storage to save protocol-specific attribute
        storage_state = self._get_browser_cookies_and_storage(context)
        local_storage = storage_state['origins'][0]['localStorage']
        progress_item = None
        for item in local_storage:
            if item['name'] == 'progress':
                progress_item = item
                break
        storage_state_to_save = {'origins': [{'origin': 'https://app.ens.domains', 'localStorage': [progress_item]}]}

        step_state = {
            "browser_storage_state": storage_state_to_save
        }

        self._update_step_state(step_state)

        return StepProcessingResult(status='success')
    
    def _perform_next_steps(self, page) -> StepProcessingResult:
        """Plan next steps based on successful execution of current step"""

        if self.curr_step.type == 'request_register':
                # Next step is to confirm registration
                description = f"ENS domain {self.ens_domain} confirm registration"

                self._create_new_curr_step("confirm_register", 2, WorkflowStepUserActionType.tx, description)
                
                # Find register button
                selector = '[data-testid="register-button"][type="primary"]'
                page.wait_for_selector(selector, timeout=TWO_MINUTES)
                page.click(selector)

        
        return StepProcessingResult(status='success')



# Invoke this with python3 -m ui_workflows.ens.ens_registration 
if __name__ == "__main__":
    tenderly_api_access_key = os.environ.get("TENDERLY_API_ACCESS_KEY", None)
    domain_to_register = "testing2304213.eth"
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
    
    tenderly_simulate_tx(tenderly_api_access_key, wallet_address, multiStepResult.tx)

    exit(0)
    
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

    tenderly_simulate_tx(tenderly_api_access_key, wallet_address, multiStepResult.tx)

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
