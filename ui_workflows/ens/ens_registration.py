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
from ..base import BaseUIWorkflow, MultiStepResult, BaseMultiStepWorkflow, WorkflowStepClientPayload, StepProcessingResult
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType
)

TWO_MINUTES = 120000
TEN_SECONDS = 10000

class ENSRegistrationWorkflow(BaseMultiStepWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_id: Optional[str], workflow_params: Dict, curr_step_client_payload: Optional[WorkflowStepClientPayload]) -> None:
        self.ens_domain = workflow_params['domain']
        rpc_urls_to_intercept = ["https://web3.ens.domains/v1/mainnet"]
        total_steps = 2
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, workflow_type, workflow_id, workflow_params, curr_step_client_payload, rpc_urls_to_intercept, total_steps)


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
        self._create_new_curr_step("request_register", 1, WorkflowStepUserActionType.tx)

        # Check for failure cases early so check if domain is already registered
        try:
            page.get_by_text("already register").wait_for()
            return StepProcessingResult(status='error', description=description, error_msg="Domain is already registered")
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

        return StepProcessingResult(status='success', description=description)
    
    def _perform_next_steps(self, page) -> StepProcessingResult:
        """Plan next steps based on successful execution of current step"""

        if self.curr_step.type == 'request_register':
                # Next step is to confirm registration
                self._create_new_curr_step("confirm_register", 2, WorkflowStepUserActionType.tx)
                
                # Find register button
                selector = '[data-testid="register-button"][type="primary"]'
                page.wait_for_selector(selector, timeout=TWO_MINUTES)
                page.click(selector)

                description = f"ENS domain {self.ens_domain} confirm registration"
        
        return StepProcessingResult(status='success', description=description)

# def tenderly_simulate_tx(tx):
#     payload = {
#       "save": True, 
#       "save_if_fails": True, 
#       "simulation_type": "full",
#       'network_id': '1',
#       'from': wallet_address,
#       'to': tx['to'],
#       'input': tx['data'],
#       'gas': int(tx['gas'], 16)
#     }

#     res = requests.post(tenderly_url, json=payload, headers={'X-Access-Key': tenderly_api_access_key })
#     print("Tenderly Simulation ID: ", res.json()["simulation"]["id"])


# Invoke this with python3 -m ui_workflows.ens.ens_registration 
if __name__ == "__main__":
    domain_to_register = "testing2304212.eth"
    wallet_address = "0x50b435d1F3C80b1015a212c6aeF29d2fa5FC1117"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    workflow_type = "register-ens-domain"
    params = {
        "domain": domain_to_register,
    }
    message_id = 'a44f1e34-4a06-411d-87f7-971ed78d7ddf'

    tx = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, message_id, workflow_type, None, params, None).run()
    print(tx)

    # workflow_id = "a518de70-c753-4b7d-b656-acf67050ec8a"
    # curr_step_client_payload = {
    #     "id": "76d24109-8b7a-431e-9967-98ae7769ebe6",
    #     "type": "request_register",
    #     "status": "success",
    #     "status_message": "TX successfully sent",
    #     "user_action_data": "TX HASH 123"
    # }

    # tx = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, message_id, workflow_type, workflow_id, params, curr_step_client_payload).run()
    # print(tx)

    #     workflow: {
    #     id: '123',
    #     operation: 'ens_registration',
    #     step: {
    #         id: '456',
    #         name: 'request_register',
    #         status: 'success',
    #         status_message: ''
    #     }
    
    # }

    # domain_to_register = "testing2304181.eth"
    # wallet_address = "0x50b435d1F3C80b1015a212c6aeF29d2fa5FC1117"
    # tenderly_api_access_key = os.environ.get("TENDERLY_API_ACCESS_KEY", None)

    # print("Start ETH Balance:", w3.eth.get_balance(wallet_address))

    # tenderly_url = f"https://api.tenderly.co/api/v1/account/Yield/project/chatweb3/fork/902db63e-9c5e-415b-b883-5701c77b3aa7/simulate"
    # wallet_chain_id = 1  # Tenderly Mainnet Fork

    # workflow_id = str(uuid.uuid4())
    # operation = "register"
    # params = {
    #     "ens_domain": domain_to_register,
    # }
    # print("Registering ENS domain: ", domain_to_register)

    # print("Step 1: Request to register ENS domain...")
    # tx = ENSUIWorkflow(wallet_chain_id, wallet_address, workflow_id, operation, params).run()[0]
    # tenderly_simulate_tx(tx)
    # print("Step 1: Request successfull")
    # print("Current ETH Balance:", w3.eth.get_balance(wallet_address))

    # print("Step 2: Confirm registration")

    # mock_db[workflow_id] = WorkflowState(workflow_id, operation, params, 'request_register', {
    #     'request_register': {
    #         'storage_stage': temp_storage_state
    #     }
    # })
    # tx = ENSUIWorkflow(wallet_chain_id, wallet_address, workflow_id, operation, params).run()[0]
    # tenderly_simulate_tx(tx)
    # print("Domain registered!")
