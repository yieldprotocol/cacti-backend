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
from ...base import BaseUIWorkflow, MultiStepResult, BaseMultiStepUIWorkflow, WorkflowStepClientPayload, StepProcessingResult, RunnableStep, tenderly_simulate_tx, setup_mock_db_objects, process_result_and_simulate_tx, fetch_multistep_workflow_from_db
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)

class AaveSupplyUIWorkflow(BaseMultiStepUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params["token"]
        self.amount = workflow_params["amount"]

        # Only one step for ETH as it doesn't require an approval step unlike ERC20 tokens
        if self.token == "ETH":
            only_step = RunnableStep("confirm_supply", WorkflowStepUserActionType.tx, f"Confirm supply of {self.amount} ETH into Aave", self.confirm_ETH_supply_step)
            steps = [only_step]
        else:
            # For ERC20 to handle approval before final confirmation
            step1 = RunnableStep("initiate_approval", WorkflowStepUserActionType.tx, f"Approve supply of {self.amount} {self.token} into Aave", self.initiate_ERC20_approval_step)
            step2 = RunnableStep("confirm_supply", WorkflowStepUserActionType.tx, f"Confirm supply of {self.amount} {self.token} into Aave", self.confirm_ERC20_supply_step)
            steps = [step1, step2]

        # This is ONLY needed when workflow has steps that replace one another conditionally eg. workflows that have ERC20 approvals 
        final_step_type = "confirm_supply"
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, workflow_type, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def _goto_page_and_open_walletconnect(self, page):
        """Go to page and open WalletConnect modal"""
        page.goto("https://app.aave.com/")
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()
    

    def initiate_ERC20_approval_step(self, page, context) -> StepProcessingResult:
        """Initiate approval for ERC20 token"""
        result = self._find_and_fill_amount_helper(page)
        if result and result.status == "error":
            return result
        
        # Click approve
        try:
            page.get_by_role("button", name="Approve").click()
        except PlaywrightTimeoutError:
            # If approval button not found in the UI modal, it means that the token is already approved so replace with final next step which is to confirm supply
            return StepProcessingResult(status="replace", replace_with_step_type="confirm_supply", replace_extra_params={"handle_replace": True})


        return StepProcessingResult(status="success")
        
    def confirm_ERC20_supply_step(self, page, context, extra_params=None) -> StepProcessingResult:
        """Confirm supply of ETH/ERC20 token"""

        # Check if this step is being run as a replacement for the approval step
        if extra_params and extra_params["handle_replace"]:
            # Fill in the amount
            page.get_by_placeholder("0.00").fill(str(self.amount))
        else:
            result = self._find_and_fill_amount_helper(page)
            if result and result.status == "error":
                return result

        # Click supply confirm
        page.get_by_role("button", name="Supply").click()

        return StepProcessingResult(status="success")
    
    def confirm_ETH_supply_step(self, page, context) -> StepProcessingResult:
        """Confirm supply of ETH/ERC20 token"""

        result = self._find_and_fill_amount_helper(page)
        if result and result.status == "error":
            return result

        # Click supply confirm
        page.get_by_role("button", name="Supply").click()

        return StepProcessingResult(status="success")
    
    def _find_and_fill_amount_helper(self, page) -> Optional[StepProcessingResult]:
        # After WC is connected, wait for page to load user's profile
        page.get_by_text("Your supplies").wait_for()

        # Find token for an operation and click it
        try:
            regex =  r"^{token}.*Supply.*$".format(token=self.token)
            page.locator("div").filter(has_text=re.compile(regex)).get_by_role("button", name="Supply").click()
        except PlaywrightTimeoutError:
            return StepProcessingResult(
                status="error", error_msg=f"Token {self.token} not found on user's profile"
            )

        # Fill in the amount
        page.get_by_placeholder("0.00").fill(str(self.amount))
        return None


# Invoke this with python3 -m ui_workflows.__aave.ui_integration.aave_supply_ui_workflow
if __name__ == "__main__":
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
