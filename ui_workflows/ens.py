import re
from logging import basicConfig, INFO
import time
import json
import uuid
import requests
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict
from .base import BaseUIWorkflow, handle_rpc_node_reqs, Result
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from utils import TENDERLY_FORK_URL, w3
import os
import env
from database.models import (
    db_session, Workflow, WorkflowStep, WorkflowStepStatus
)


TWO_MINUTES = 120000


class ENSUIWorkflow(BaseUIWorkflow):

    def __init__(self, session_id: str, message_id: str, wallet_chain_id: int, wallet_address: str, workflow_id: Optional[str], curr_step_client_payload: Optional[Dict], operation: str, params: Dict) -> None:
        self.session_id = session_id
        self.message_id = message_id
        self.workflow_id = workflow_id
        self.curr_step_client_payload = curr_step_client_payload
        self.operation = operation
        self.params = params
        self.step = None

        parsed_user_request = f"message_id: {self.message_id}, wf_id: {self.workflow_id}, operaton: {self.operation} params: {self.params}"
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

    def _before_run(self) -> None:
        # Retrive any browser storage state for the step and update the step status
        if self.curr_step_client_payload:
            self.step = WorkflowStep.query.filter(WorkflowStep.id == self.curr_step_client_payload['id']).first()
            self.browser_storage_state = self.step.step_state['storage_state']
            self.step.status = WorkflowStepStatus[self.curr_step_client_payload['status']]
            self.step.status_message = self.curr_step_client_payload['status_message']
            db_session.commit()
    
    def _run_page(self, page, context):
        try:
            # Intercept protocol's requests to its own RPC node
            if not env.is_prod():
                page.route("https://web3.ens.domains/v1/mainnet", self._intercept_for_register_op)

            ens_domain = self.params['ens_domain']

            if self.operation == "ens_registration":
                page.goto(f"https://app.ens.domains/name/{ens_domain}/register")

                # Find connect wallet and retrieve WC URI
                page.get_by_text("Connect", exact=True).click()
                page.get_by_text("WalletConnect", exact=True).click()
                page.get_by_text("Copy to clipboard").click()
                wc_uri = page.evaluate("() => navigator.clipboard.readText()")
                self.start_listener(wc_uri)
                
                if not self.step:
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

                    # TODO: remove below lines
                    global temp_storage_state
                    temp_storage_state = storage_state_to_save
                    workflow = Workflow(
                        id=str(uuid.uuid4()),
                        session_id=self.session_id,
                        message_id=self.message_id,
                        operation=self.operation,
                        params=self.params,
                    )
                    workflow_step = WorkflowStep(
                        workflow_id=workflow.id,
                        name="request_register",
                        status=WorkflowStepStatus.pending,
                        step_state={
                            "storage_state": storage_state_to_save
                        }
                    )
                    db_session.add_all([workflow, workflow_step])
                    db_session.commit()
                
                elif self.step.name == 'request_register':
                    # Process and update payload
                    if self.step.status == WorkflowStepStatus.success:
                        # Confirm register button
                        selector = '[data-testid="register-button"][type="primary"]'
                        page.wait_for_selector(selector, timeout=TWO_MINUTES)
                        page.click(selector)
                        workflow_step = WorkflowStep(
                            workflow_id=self.workflow_id,
                            name="confirm_register",
                            status=WorkflowStepStatus.pending,
                        )
                        db_session.add(workflow_step)
                        db_session.commit()


            page.wait_for_timeout(5000)
            tx = self.stop_listener()
            return tx
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


# Invoke this with python3 -m ui_workflows.ens
if __name__ == "__main__":
    domain_to_register = "testing2304181.eth"
    wallet_address = "0x50b435d1F3C80b1015a212c6aeF29d2fa5FC1117"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    operation = "ens_registration"
    params = {
        "ens_domain": domain_to_register,
    }
    session_id = 'b5fe603f-ecc9-4379-9f8c-f5150a468893'
    message_id = 'a44f1e34-4a06-411d-87f7-971ed78d7ddf'
    
    # tx = ENSUIWorkflow(session_id, message_id, wallet_chain_id, wallet_address, None, None, operation, params).run()[0]
    # print(tx)

    workflow_id = 'debf0284-c767-4519-bb2e-71462abd4c85'
    curr_step_client_payload = {
        "id": "03b3ba3e-aef1-46c0-9b78-f2d7c7c23a0c",
        "name": "request_register",
        "status": "success",
        "status_message": ""
    }

    tx = ENSUIWorkflow(session_id, message_id, wallet_chain_id, wallet_address, workflow_id, curr_step_client_payload, operation, params).run()[0]
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
