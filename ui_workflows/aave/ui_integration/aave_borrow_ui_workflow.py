import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

from ...base import BaseSingleStepUIWorkflow, StepProcessingResult, BaseMultiStepUIWorkflow, RunnableStep, WorkflowStepClientPayload
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)
from ..common import AaveMixin, FIVE_SECONDS

class AaveBorrowUIWorkflow(AaveMixin, BaseMultiStepUIWorkflow):
    """
    UI Workflow script for borrowing tokens on Aave. This workflow handles borrowing for both ETH and ERC20 tokens.

    The workflow handles the following scenarios:

    * User tries to borrow more ETH/ERC20 than their balance
    - Aave UI will auto-change/override user amount to the max allowed and show a warning text along with a checkbox to acknowledge the liquidation risk
    - The script will check for this scenario by looking for the warning text on the UI and if found will return a result with action type "acknowledge" to get user's explicit approval in the Chat UI
    - Since Aave UI auto-changes/overrides the amount to the max allowed, the script will get the new amount and override the user description so that the new amount in displayed to the user
    - If this scenario is not encountered, the step will be replaced by the next step which is to check if ETH requires approval

    * ETH requires approval as part of variable debt delegation https://docs.aave.com/developers/tokens/debttoken#approvedelegation
    - Aave UI will show an approval button with the confirm button disabled
    - The script will check for this by looking for the approval button on the UI and if found will click it to get the tx params via WalletConnect client and return that in the result with action type "tx" to get user to sign and confirm the tx in their wallet
    - if this scenario is not encountered, the step will be replaced by the next step which is to confirm the borrow

    * Confirm ETH/ERC20 borrow
    - Aave UI will show a confirm button in a modal
    - The script will check for this by looking for the confirm button and click it to get the tx params via WalletConnect client and return that in the result with action type "tx" to get user to sign and confirm the tx in their wallet

    This workflow handles the following error cases:
    * Token not available in user's profile, for this this the script will throw a timeout exception on not finding the token and return result with error status and message.
    """
        
    WORKFLOW_TYPE = 'aave-borrow'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params["token"]
        self.amount = workflow_params["amount"]

        if self.token == "ETH":
            check_ETH_liquidation_risk_step = RunnableStep("check_ETH_liquidation_risk", WorkflowStepUserActionType.acknowledge, f"Acknowledge liquidation risk due to high borrow amount of {self.amount} ETH on Aave", self.check_ETH_liquidation_risk)
            initiate_ETH_approval_step = RunnableStep("initiate_ETH_approval", WorkflowStepUserActionType.tx, f"Approve borrow of {self.amount} ETH on Aave", self.initiate_ETH_approval)
            confirm_ETH_borrow_step = RunnableStep("confirm_ETH_borrow", WorkflowStepUserActionType.tx, f"Confirm borrow of {self.amount} ETH on Aave", self.confirm_ETH_borrow)
            steps = [check_ETH_liquidation_risk_step, initiate_ETH_approval_step, confirm_ETH_borrow_step]
            
            final_step_type = "confirm_ETH_borrow"
        else:
            check_ERC20_liquidation_risk = RunnableStep("check_ERC20_liquidation_risk", WorkflowStepUserActionType.acknowledge, f"Acknowledge liquidation risk due to high borrow amount of {self.amount} {self.token} on Aave", self.check_ERC20_liquidation_risk)
            confirm_ERC20_borrow_step = RunnableStep("confirm_ERC20_borrow", WorkflowStepUserActionType.tx, f"Confirm borrow of {self.amount} {self.token} from Aave", self.confirm_ERC20_borrow)
            steps = [check_ERC20_liquidation_risk, confirm_ERC20_borrow_step]
            final_step_type = "confirm_ERC20_borrow"

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, self.WORKFLOW_TYPE, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def check_ETH_liquidation_risk(self, page, browser_context):
        
        result = self._find_and_fill_amount_helper(page, "Borrow")
        if result and result.status == "error":
            return result
        
        try:
            page.get_by_text("acknowledge the risks").wait_for(timeout=FIVE_SECONDS)
        except PlaywrightTimeoutError:
            # If acknowledge the risk message not found in the UI modal, it means that token amount is within limit so replace with final next step which is to intiate ETH approval
            return StepProcessingResult(status="replace", replace_with_step_type="initiate_ETH_approval", replace_extra_params={"handle_replace": True})
    
        # Override user amount to use the one set by Aave UI as it can automatically change it to the highest possible value if the user enters an amount that is too high
        overriden_amount = page.get_by_placeholder("0.00").input_value()
        return StepProcessingResult(status="success", override_user_description=f"Acknowledge liquidation risk due to high borrow amount of {overriden_amount} ETH on Aave")

    def initiate_ETH_approval(self, page, browser_context, extra_params=None):
        """Initiate approval for ETH token"""      

        # If this step is not triggered by a replace, then it was triggered as part of the normal next step processing flow after user accepted liquidation risk from Chat UI so make sure to check the checkbox 
        if not (extra_params and extra_params["handle_replace"]):
            result = self._find_and_fill_amount_helper(page, "Borrow")
            if result and result.status == "error":
                return result
            page.locator("div").filter(has_text=re.compile(r"^I acknowledge the risks involved\.$")).get_by_role("checkbox").check()

        # Click approve
        try:
            page.get_by_role("button", name="Approve").click(timeout=FIVE_SECONDS)
        except PlaywrightTimeoutError:
            # If approval button not found in the UI modal, it means that ETH is already approved so replace with final next step which is to confirm borrow
            return StepProcessingResult(status="replace", replace_with_step_type="confirm_ETH_borrow", replace_extra_params={"handle_replace": True})

        overriden_amount = page.get_by_placeholder("0.00").input_value()
        return StepProcessingResult(status="success", override_user_description=f"Approve borrow of {overriden_amount} ETH on Aave")

    def confirm_ETH_borrow(self, page, browser_context, extra_params=None):

        if not (extra_params and extra_params["handle_replace"]):
            result = self._find_and_fill_amount_helper(page, "Borrow")
            if result and result.status == "error":
                return result
                
        page.get_by_role("button", name="Borrow").click()

        overriden_amount = page.get_by_placeholder("0.00").input_value()
        return StepProcessingResult(status="success", override_user_description=f"Confirm borrow of {overriden_amount} ETH on Aave")


    def check_ERC20_liquidation_risk(self, page, browser_context):   
        result = self._find_and_fill_amount_helper(page, "Borrow")
        if result and result.status == "error":
            return result
        
        try:
            page.get_by_text("acknowledge the risks").wait_for(timeout=FIVE_SECONDS)
        except PlaywrightTimeoutError:
            # If acknowledge the risk message not found in the UI modal, it means that token amount is within limit so replace with final next step which is to confirm borrow
            return StepProcessingResult(status="replace", replace_with_step_type="confirm_ERC20_borrow", replace_extra_params={"handle_replace": True})
    
        overriden_amount = page.get_by_placeholder("0.00").input_value()
        return StepProcessingResult(status="success", override_user_description=f"Acknowledge liquidation risk due to high borrow amount of {overriden_amount} {self.token} on Aave")
    
    def confirm_ERC20_borrow(self, page, browser_context, extra_params=None):

        if not (extra_params and extra_params["handle_replace"]):
            result = self._find_and_fill_amount_helper(page, "Borrow")
            if result and result.status == "error":
                return result
                
        page.get_by_role("button", name="Borrow").click()

        overriden_amount = page.get_by_placeholder("0.00").input_value()
        return StepProcessingResult(status="success", override_user_description=f"Confirm borrow of {overriden_amount} {self.token} on Aave")