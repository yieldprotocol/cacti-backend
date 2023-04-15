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
from utils import TENDERLY_FORK_URL

TWO_MINUTES = 120000

@dataclass
class WorkflowState:
    id: str
    operation: str
    params: Dict
    latest_step: str
    step_metadata: Dict

mock_db = {}

class ENSUIWorkflow(BaseUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, workflow_id: str, operation: str, params: Dict) -> None:
        parsed_user_request = f"{workflow_id}: {operation} {params['ens']}"
        super().__init__(wallet_chain_id, wallet_address, parsed_user_request)
        self.operation = operation
        self.params = params
        self.storage_stage = params.get('storage_stage', None)

        # TODO: Load workflow state from DB
        self.workflow_state = mock_db.get(workflow_id, None)
        if not self.workflow_state:
            self.latest_step = None
        else:
            self.latest_step = self.workflow_state.latest_step
            # Populate localStorage to allow ENS to load into the correct state
            if self.latest_step == "request_register":
                self.storage_stage = self.workflow_state.step_metadata["request_register"]["storage_stage"]
        

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

    def _run_page(self, page, context):
        try:
            ens = self.params['ens']

            if self.operation == "register":
                page.goto(f"https://app.ens.domains/name/{ens}/register")

                # Intercept protocol's requests to its own RPC node
                page.route("https://web3.ens.domains/v1/mainnet", self._intercept_for_register_op)

                # Find connect wallet and retrieve WC URI
                page.get_by_text("Connect", exact=True).click()
                page.get_by_text("WalletConnect", exact=True).click()
                page.get_by_text("Copy to clipboard").click()
                wc_uri = page.evaluate("() => navigator.clipboard.readText()")
                self.start_listener(wc_uri)

                # If no latest step found, assume it is the first step to initiate request to register
                if not self.latest_step:
                    curr_step = 'request_register'
                elif self.latest_step == 'request_register':
                    curr_step = 'confirm_register'
                

                if curr_step == 'request_register':
                    # Request to register button
                    page.get_by_test_id("request-register-button").click(timeout=TWO_MINUTES)

                    # TODO: persist storage state in new DB table "workflow_state", temporarily print out storage state
                    storage_state = context.storage_state()
                    local_storage = storage_state['origins'][0]['localStorage']

                    progress_item = None
                    for item in local_storage:
                        if item['name'] == 'progress':
                            progress_item = item
                            break
                    storage_state_to_save = {'origins': [{'origin': 'https://app.ens.domains', 'localStorage': [progress_item]}]}
                    print("STORAGE STATE TO SAVE:", storage_state_to_save)
                    
                elif curr_step == 'confirm_register':
                    page.get_by_test_id("register-button").click(timeout=TWO_MINUTES)


            page.wait_for_timeout(5000)
            tx = self.stop_listener()
        except Exception as e:
            self.stop_listener()


# Invoke this with python3 -m ui_workflows.ens
if __name__ == "__main__":
    """
    DEMO:

    1. Request to register ENS
        a. Modify below wallet_address to be your own test address
        b. Run this script
        c. Wait for browser storage state and tx params to be printed out 

    2. Confirm registration
        a. Uncomment the storage_stage variable below and paste in the storage state printed out from step 1.c
        b. Uncomment the mock_db line below
        c. Run this script
    """

    wallet_chain_id = 1  # Tenderly Mainnet Fork
    wallet_address = "0x14E3b72D6dc6EC8b3427DA4B42b713b12afD19A6"

    workflow_id = str(uuid.uuid4())
    operation = "register"
    params = {
        "ens": "testing23041442.eth",
    }


    # BELOW IS ONLY FOR STEP 2
    # storage_stage = {'origins': [{'origin': 'https://app.ens.domains', 'localStorage': [{'name': 'progress', 'value': '{"1-testing23041442":{"step":"PRICE_DECISION","secret":"0x618462db3eb1a02bad7ba4f3efdc8dda1edf7a94ac7d1652b65d9f713a099c56","years":1}}'}]}]}

    # mock_db[workflow_id] = WorkflowState(workflow_id, operation, params, 'request_register', {
    #     'request_register': {
    #         'storage_stage': storage_stage
    #     }
    # })


    wf = ENSUIWorkflow(wallet_chain_id, wallet_address, workflow_id, operation, params)
    print(wf.run())
