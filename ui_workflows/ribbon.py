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

class RibbonUIWorkflow(BaseUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, workflow_id: str, operation: str, params: Dict) -> None:
        parsed_user_request = f"{workflow_id}: {operation} {params['ens']}"
        super().__init__(wallet_chain_id, wallet_address, parsed_user_request)
        self.operation = operation
        self.params = params
        self.storage_stage = params.get('storage_stage', None)
        

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

    def _intercept(self, route):
        post_body = route.request.post_data
        # Forward request to Tenderly RPC node
        data = requests.post(TENDERLY_FORK_URL, data=post_body)
        route.fulfill(body=data.text, headers={"access-control-allow-origin": "*", "access-control-allow-methods": "*", "access-control-allow-headers": "*"})



    def _run_page(self, page, context):
        try:
            page.goto("https://app.ribbon.finance/v2/theta-vault/T-ETH-C")


            # Intercept protocol's requests to its own RPC node
            # page.route("https://eth-mainnet.alchemyapi.io/v2/vI8OBZj4Wue9yNPSDVa7Klqt-UeRywrx", self._intercept)
            page.get_by_role("button", name="CONNECT WALLET", exact=True).click()
            page.get_by_text("Ethereum").click()
            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="WALLET CONNECT").click()
            page.get_by_role("button", name="Connect", exact=True).click()
            page.get_by_text("Copy to clipboard").click()
            wc_uri = page.evaluate("() => navigator.clipboard.readText()")
            self.start_listener(wc_uri)
            page.get_by_role("spinbutton", name="ETH").click()
            page.get_by_role("spinbutton", name="ETH").fill("1")
            page.get_by_role("button", name="Preview Deposit").click()
            page.get_by_role("button", name="Deposit Now").click()
            page.route("https://eth-mainnet.alchemyapi.io/v2/vI8OBZj4Wue9yNPSDVa7Klqt-UeRywrx", self._intercept)
            rc_length = len(result_container)
            page.locator("div").filter(has_text="Confirm DepositConfirm this transaction in your wallet").nth(1).click()
            while len(result_container) == rc_length:
                pass
            
            

        except Exception as e:
            self.stop_listener()


# Invoke this with python3 -m ui_workflows.ribbon
if __name__ == "__main__":
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    workflow_id = str(uuid.uuid4())
    operation = "register"
    params = {
        "ens": "testing22539y42.eth",
    }

    wf = RibbonUIWorkflow(wallet_chain_id, wallet_address, workflow_id, operation, params)
    print(wf.run())
