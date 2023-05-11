import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

from ...base import BaseSingleStepUIWorkflow, StepProcessingResult, tenderly_simulate_tx
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class AaveETHSupplyUIWorkflow(BaseSingleStepUIWorkflow):
    """
    Workflow for supplying ETH to Aave

    NOTE: Only for demo purposes to show a single-step approach example but may NOT be an optimal approach, also see the multi-step variant of this workflow
    
    """

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict):
        # self.token = workflow_params["token"]
        self.token = "ETH" # hard-coding ETH for demo purposes
        self.amount = workflow_params["amount"]


        user_description = f"Supply {self.amount} {self.token} to Aave"
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, workflow_type, workflow_params, user_description)

    def _goto_page_and_open_walletconnect(self, page):
        page.goto("https://app.aave.com/")
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()

    def _run_step(self, page, context) -> StepProcessingResult:
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

            # Click confirm
            page.get_by_role("button", name="Supply").click()

            return StepProcessingResult(status="success")



# Invoke this with python3 -m ui_workflows.__aave.ui_integration.aave_eth_supply_single_step_demo
if __name__ == "__main__":
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    mock_chat_message_id = str(uuid.uuid4())
    workflow_type = "aave-supply"
    token = "ETH"
    operation = "Supply"
    amount = 0.1
    workflow_params = {"token": token, "amount": amount}

    result = AaveETHSupplyUIWorkflow(wallet_chain_id, wallet_address, mock_chat_message_id, workflow_type, workflow_params).run()

    if result.status == "success":
        tenderly_simulate_tx(wallet_address, result.tx)
        print("Workflow successful")
    else:
        print("Workflow failed")
