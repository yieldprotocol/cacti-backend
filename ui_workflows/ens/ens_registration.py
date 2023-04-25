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

class ENSRegistrationWorkflow(BaseMultiStepWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict, workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.ens_domain = workflow_params['domain']

        step1 = RunnableStep("request_register", WorkflowStepUserActionType.tx, f"ENS domain {self.ens_domain} request registration", self.step_1_request_register)
        step2 = RunnableStep("confirm_register", WorkflowStepUserActionType.tx, f"ENS domain {self.ens_domain} confirm registration", self.step_2_confirm_registration)

        steps = [step1, step2]
        
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

        page.goto(f"https://legacy.ens.domains/name/{self.ens_domain}/register")

        # Search for WalletConnect and open QRCode modal
        page.get_by_role("navigation").get_by_text("Connect").click()
        page.get_by_text("WalletConnect", exact=True).click()

    def step_1_request_register(self, page, context) -> StepProcessingResult:
        """Step 1: Request registration"""

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

        # Preserve browser local storage item to allow protocol to recreate the correct state
        self._preserve_browser_local_storage_item(context, 'progress')

        return StepProcessingResult(status='success')
    
    def step_2_confirm_registration(self, page, context) -> StepProcessingResult:
        """Step 2: Confirm registration"""

        # Find register button
        selector = '[data-testid="register-button"][type="primary"]'

        # The 2 minutes timeout allows for the ENS 1 minute wait time to be completed
        page.wait_for_selector(selector, timeout=TWO_MINUTES)
        page.click(selector)

        return StepProcessingResult(status='success')