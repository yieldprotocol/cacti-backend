import re
from logging import basicConfig, INFO
import time
import json
import uuid
import requests
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict
from ..base import BaseUIWorkflow, MultiStepResult
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from utils import TENDERLY_FORK_URL, w3
import os
import env
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus
)


TWO_MINUTES = 120000


class ENSRegistrationWorkflow(BaseUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_id: Optional[str], params: Dict, curr_step_client_payload: Optional[Dict]) -> None:
        self.chat_message_id = chat_message_id
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.curr_step_client_payload = curr_step_client_payload
        self.workflow_type = workflow_type
        self.params = params
        self.curr_step = None
        self.ens_domain = params['domain']

        parsed_user_request = f"chat_message_id: {self.chat_message_id}, wf_id: {self.workflow_id}, workflow_type: {self.workflow_type}, params: {self.params}"
        super().__init__(wallet_chain_id, wallet_address, parsed_user_request)

    def _intercept_for_register_op(self, route):
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
        else:
            data = requests.post(TENDERLY_FORK_URL, data=post_body)
            res_text = data.text
        route.fulfill(body=res_text, headers={"access-control-allow-origin": "*", "access-control-allow-methods": "*", "access-control-allow-headers": "*"})

    def _before_page_run(self) -> None:
        # Retrive any browser storage state for the step and update the step status
        if self.curr_step_client_payload:
            self.curr_step = WorkflowStep.query.filter(WorkflowStep.id == self.curr_step_client_payload['id']).first()
            self.browser_storage_state = self.curr_step.step_state['browser_storage_state']
            self.curr_step.status = WorkflowStepStatus[self.curr_step_client_payload['status']]
            self.curr_step.status_message = self.curr_step_client_payload['status_message']
            db_session.commit()
    
    def _run_page(self, page, context) -> MultiStepResult:
        try:
            # Intercept protocol's requests to its own RPC node
            if not env.is_prod():
                page.route("https://web3.ens.domains/v1/mainnet", self._intercept_for_register_op)


            page.goto(f"https://app.ens.domains/name/{self.ens_domain}/register")

            # Find connect wallet and retrieve WC URI
            page.get_by_text("Connect", exact=True).click()
            page.get_by_text("WalletConnect", exact=True).click()
            page.get_by_text("Copy to clipboard").click()
            wc_uri = page.evaluate("() => navigator.clipboard.readText()")
            self.start_listener(wc_uri)
            
            description = ''
            if not self.curr_step:
                # create new step
                # Request to register button

                # Button is not using html standard disabled property, instead using "type" attribute
                selector = '[data-testid="request-register-button"][type="primary"]'
                page.wait_for_selector(selector, timeout=TWO_MINUTES)
                page.click(selector)

                # TODO: persist storage state in new DB table "workflow_state", temorarily save to temp_storage_state
                storage_state = context.storage_state()
                local_storage = storage_state['origins'][0]['localStorage']

                progress_item = None
                for item in local_storage:
                    if item['name'] == 'progress':
                        progress_item = item
                        break
                storage_state_to_save = {'origins': [{'origin': 'https://app.ens.domains', 'localStorage': [progress_item]}]}
                print("progress_item: ", progress_item)
                workflow = MultiStepWorkflow(
                    id=self.workflow_id,
                    chat_message_id=self.chat_message_id,
                    type=self.workflow_type,
                    params=self.params,
                )
                workflow_step = WorkflowStep(
                    workflow_id=workflow.id,
                    type="request_register",
                    status=WorkflowStepStatus.pending,
                    step_state={
                        "browser_storage_state": storage_state_to_save
                    }
                )
                db_session.add_all([workflow, workflow_step])
                db_session.commit()
                self.curr_step = workflow_step
                description = f"Step 1: ENS domain {self.ens_domain} request registration"
            
            elif self.curr_step.type == 'request_register':
                # Process and update payload
                if self.curr_step.status == WorkflowStepStatus.success:
                    # Confirm register button
                    selector = '[data-testid="register-button"][type="primary"]'
                    page.wait_for_selector(selector, timeout=TWO_MINUTES)
                    page.click(selector)
                    workflow_step = WorkflowStep(
                        workflow_id=self.workflow_id,
                        type="confirm_register",
                        status=WorkflowStepStatus.pending,
                    )
                    db_session.add(workflow_step)
                    db_session.commit()
                    self.curr_step = workflow_step
                    description = f"Step 2: ENS domain {self.ens_domain} confirm registration"


            page.wait_for_timeout(5000)
            tx = self.stop_listener()
            return MultiStepResult(
                status='success',
                workflow_id=str(self.workflow_id),
                workflow_type=self.workflow_type,
                step_id=str(self.curr_step.id),
                step_type=self.curr_step.type,
                user_action_type="tx",
                tx=tx,
                description=description
            )
        except Exception as e:
            print(e)
            self.stop_listener()

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
    domain_to_register = "testing2304201.eth"
    wallet_address = "0xA7EdB4fb2543faca974030580691229F9076F5b7"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    workflow_type = "register-ens-domain"
    params = {
        "domain": domain_to_register,
    }
    message_id = 'a44f1e34-4a06-411d-87f7-971ed78d7ddf'
     

    # tx = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, message_id, workflow_type, None, params, None).run()
    # print(tx)

    workflow_id = 'e3e166a6-8e35-437a-adcc-965611a938be'
    curr_step_client_payload = {
        "id": "9b2b056a-86ae-4d8e-adb0-928e45db5505",
        "type": "request_register",
        "status": "success",
        "status_message": ""
    }

    tx = ENSRegistrationWorkflow(wallet_chain_id, wallet_address, message_id, workflow_type, workflow_id, params, curr_step_client_payload).run()
    print(tx)

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
