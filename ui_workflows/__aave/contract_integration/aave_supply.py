import re
from logging import basicConfig, INFO
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable

from ...base import BaseMultiStepContractWorkflow, Result, RunnableStep
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)

class AaveSupplyWorkflow(BaseMultiStepContractWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow: Optional[MultiStepWorkflow], workflow_params: Dict, curr_step_client_payload: Optional[WorkflowStepClientPayload], runnable_steps: List[RunnableStep], contract_address: str, abi_path: str):
        """
        TODO:
        - change to use mapping of abi_path to arbitrary key
        - store token contract address and other metadata such as permit function support
        - while implementing protocol functions prefer permit function over approve
        - ENS Add error check for domain ownership
        """
        
        self.ens_domain = workflow_params['domain']

        step1 = RunnableStep("request_registration", WorkflowStepUserActionType.tx, f"ENS domain {self.ens_domain} request registration", self.step_1_request_registration)
        step2 = RunnableStep("confirm_registration", WorkflowStepUserActionType.tx, f"ENS domain {self.ens_domain} confirm registration", self.step_2_confirm_registration)

        steps = [step1, step2]
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, workflow_type, workflow, workflow_params, curr_step_client_payload, steps)

    def _goto_page_and_open_walletconnect(self, page):
        page.goto("https://app.aave.com/")
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()


# Invoke this with python3 -m ui_workflows.aave
if __name__ == "__main__":
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    token = "ETH"
    operation = "Supply"
    amount = 0.1

    # token = "USDT"
    # operation = "Borrow"
    # amount = 1

    # token = "USDC"
    # operation = "Repay"
    # amount = 200

    # token = "ETH"
    # operation = "Withdraw"
    # amount = 0.2
    wf = AaveUIWorkflow(wallet_chain_id, wallet_address, token, operation, amount)
    print(wf.run())
