import re
from logging import basicConfig, INFO
import time
import json
import uuid
import os
import requests
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import env
from utils import TENDERLY_FORK_URL, w3
from ..base import BaseUIWorkflow, MultiStepResult, BaseMultiStepWorkflow, WorkflowStepClientPayload, StepProcessingResult, RunnableStep, tenderly_simulate_tx, setup_mock_db_objects
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)

TWO_MINUTES = 120000
TEN_SECONDS = 10000

class CompoundBorrowWorkflow(BaseMultiStepWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict, workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params['token']
        self.amount = workflow_params['amount']

        step1 = RunnableStep("confirm_borrow", WorkflowStepUserActionType.tx, f"{self.token} confirm borrow", self.step_1_confirm_borrow)

        steps = [step1]
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, workflow_type, workflow, workflow_params, curr_step_client_payload, steps)


    def _forward_rpc_node_reqs(self, route):
        """Override to intercept requests to ENS API and modify response to simulate block production"""
        post_body = route.request.post_data
        
        # Intercepting below request to modify timestamp to be 5 minutes in the future to simulate block production and allow ENS web app to not be stuck in waiting loop
        if "eth_getBlockByNumber" in post_body:
            curr_time_hex = hex(int(time.time()) + 300)
            data = requests.post(TENDERLY_FORK_URL, data=post_body)
            json_dict = data.json()
            json_dict["result"]["timestamp"] = curr_time_hex
            data = json_dict
            res_text = json.dumps(data)
            route.fulfill(body=res_text, headers={"access-control-allow-origin": "*", "access-control-allow-methods": "*", "access-control-allow-headers": "*"})
        else:
            super()._forward_rpc_node_reqs(route)

    def _goto_page_and_open_walletconnect(self, page):
        """Go to page and open WalletConnect modal"""

        page.goto(f"https://v2-app.compound.finance/")

        # Search for WalletConnect and open QRCode modal
        page.locator("a").filter(has_text="Wallet Connect").click()

    def step_1_confirm_borrow(self, page, context) -> StepProcessingResult:
        """Step 1: Confirm borrow"""
        # Find the token
        try:
            token_locators = page.get_by_text(re.compile(r".*\s{token}.*".format(token=self.token)))
        except PlaywrightTimeoutError:
            return StepProcessingResult(status='error', error_msg=f"{self.token} not available for Borrow")
        
        # Find borrow
        for i in range(4):
            try: token_locators.nth(i).click()
            except: continue
            if page.locator("label").filter(has_text=re.compile(r"^Borrow$")).is_visible():
                page.locator("label").filter(has_text=re.compile(r"^Borrow$")).click()
                break
            page.locator(".close-x").click()

        # Fill the amount
        page.get_by_placeholder("0").fill(str(self.amount))
        try:
            page.get_by_role("button", name="Borrow").click()
        except PlaywrightTimeoutError:
            return StepProcessingResult(status='error', error_msg=f"No Balance to Borrow {self.amount} {self.token}")

        return StepProcessingResult(status='success')