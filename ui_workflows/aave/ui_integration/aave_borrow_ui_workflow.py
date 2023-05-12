import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

from ...base import BaseSingleStepUIWorkflow, StepProcessingResult, BaseMultiStepUIWorkflow, RunnableStep
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)
from .common import AaveMixin

class AaveBorrowUIWorkflow(AaveMixin, BaseMultiStepUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params["token"]
        self.amount = workflow_params["amount"]

        # Only one step for ETH as it doesn't require an approval step unlike ERC20 tokens
        if self.token == "ETH":
            initiate_approval_step = RunnableStep("initiate_approval", WorkflowStepUserActionType.tx, f"Approve borrow of {self.amount} ETH on Aave", self.initiate_eth_approval)
            check_liquidation_risk = RunnableStep("check_liquidation_risk", WorkflowStepUserActionType.acknowledge, f"Acknowledge liquidation risk due to high borrow amount of {self.amount} ETH on Aave", self.check_liquidation_risk)
            confirm_borrow_step = RunnableStep("confirm_borrow", WorkflowStepUserActionType.tx, f"Confirm borrow of {self.amount} ETH on Aave", self.confirm_eth_borrow)
            steps = [initiate_approval_step, check_liquidation_risk, confirm_borrow_step]
        else:
            # For ERC20 to handle approval before final confirmation
            check_liquidation_risk = RunnableStep("check_liquidation_risk", WorkflowStepUserActionType.acknowledge, f"Acknowledge liquidation risk due to high borrow amount of {self.amount} {self.token} on Aave", self.check_liquidation_risk)
            confirm_borrow_step = RunnableStep("confirm_borrow", WorkflowStepUserActionType.tx, f"Confirm borrow of {self.amount} {self.token} from Aave", self.confirm_erc20_borrow)
            steps = [check_liquidation_risk, confirm_borrow_step]

        # NOTE: This is ONLY needed when workflow has steps that replace one another conditionally eg. workflows that have ETH approvals like this one
        final_step_type = "confirm_borrow"

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, workflow_type, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def initiate_eth_approval(self, page, context):
        pass

    def confirm_eth_borrow(self, page, context):
        pass

    def check_liquidation_risk(self, page, context):
        pass

    def confirm_erc20_borrow(self, page, context):
        # After WC is connected, wait for page to load user's profile
        page.get_by_text("Your supplies").wait_for()

        # TODO: handle the edge case of too high amount, if a really high maount is entered the UI auto changes it so return that as part of the message

        # self.prev_step.user_action_type = WorkflowStepUserActionType.acknowledge
        # self.prev_step.user_action_data = "accept"

        # Find token for an operation and click it
        try:
            regex =  r"^{token}.*BorrowDetails$".format(token=self.token)
            page.locator("div").filter(has_text=re.compile(regex)).get_by_role("button", name="Borrow").click()
        except PlaywrightTimeoutError:
            return StepProcessingResult(
                status="error", error_msg=f"Token {self.token} not found on user's profile"
            )

        # Fill in the amount
        page.get_by_placeholder("0.00").fill(str(self.amount))

        # Click confirm
        page.get_by_role("button", name="Borrow").click()

        return StepProcessingResult(status="success") 

