import re
from logging import basicConfig, INFO
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import env
from utils import TENDERLY_FORK_URL, w3
from ...base import BaseMultiStepUIWorkflow, WorkflowStepClientPayload, StepProcessingResult, RunnableStep
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)
from .common import AaveMixin, FIVE_SECONDS

class AaveSupplyUIWorkflow(AaveMixin, BaseMultiStepUIWorkflow):
    WORKFLOW_TYPE = 'aave-supply'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params["token"]
        self.amount = workflow_params["amount"]

        # Only one step for ETH as it doesn't require an approval step unlike ERC20 tokens
        if self.token == "ETH":
            confirm_ETH_supply_step = RunnableStep("confirm_ETH_supply", WorkflowStepUserActionType.tx, f"Confirm supply of {self.amount} ETH into Aave", self.confirm_ETH_supply_step)
            steps = [confirm_ETH_supply_step]
            final_step_type = "confirm_ETH_supply"
        else:
            # For ERC20 you have to handle approval before final confirmation
            initiate_ERC20_approval_step = RunnableStep("initiate_ERC20_approval", WorkflowStepUserActionType.tx, f"Approve supply of {self.amount} {self.token} into Aave", self.initiate_ERC20_approval_step)
            confirm_ERC20_supply_step = RunnableStep("confirm_ERC20_supply", WorkflowStepUserActionType.tx, f"Confirm supply of {self.amount} {self.token} into Aave", self.confirm_ERC20_supply_step)
            steps = [initiate_ERC20_approval_step, confirm_ERC20_supply_step]

            final_step_type = "confirm_ERC20_supply"
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, self.WORKFLOW_TYPE, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

 
    def confirm_ETH_supply_step(self, page, context) -> StepProcessingResult:
        """Confirm supply of ETH/ERC20 token"""

        result = self._find_and_fill_amount_helper(page, "Supply")
        if result and result.status == "error":
            return result

        # Click supply confirm
        page.get_by_role("button", name="Supply").click()

        # Override user amount to use the one set by Aave UI as it can automatically change it to the highest possible value if the user enters an amount that is too high
        overriden_amount = page.get_by_placeholder("0.00").input_value()
        return StepProcessingResult(status="success", override_user_description=f"Confirm supply of {overriden_amount} ETH into Aave")
    
    def initiate_ERC20_approval_step(self, page, context) -> StepProcessingResult:
        """Initiate approval for ERC20 token"""
        result = self._find_and_fill_amount_helper(page, "Supply")
        if result and result.status == "error":
            return result
        
        # Click approve
        try:
            page.get_by_role("button", name="Approve").click(timeout=FIVE_SECONDS)
        except PlaywrightTimeoutError:
            # If approval button not found in the UI modal, it means that the token is already approved so replace with final next step which is to confirm supply
            return StepProcessingResult(status="replace", replace_with_step_type="confirm_ERC20_supply", replace_extra_params={"handle_replace": True})


        return StepProcessingResult(status="success")
        
    def confirm_ERC20_supply_step(self, page, context, extra_params=None) -> StepProcessingResult:
        """Confirm supply of ETH/ERC20 token"""

        # Check if this step is being run as a replacement for the approval step
        if extra_params and extra_params["handle_replace"]:
            # If it is a replacement, then proceed to fill the amount as the UI modal to supply is already open from previou step and no need to find the token
            page.get_by_placeholder("0.00").fill(str(self.amount))
        else:
            result = self._find_and_fill_amount_helper(page, "Supply")
            if result and result.status == "error":
                return result

        # Click supply confirm
        page.get_by_role("button", name="Supply").click()

        # Override user amount to use the one set by Aave UI as it can automatically change it to the highest possible value if the user enters an amount that is too high
        overriden_amount = page.get_by_placeholder("0.00").input_value()
        return StepProcessingResult(status="success", override_user_description=f"Confirm supply of {overriden_amount} {self.token} into Aave")
   
