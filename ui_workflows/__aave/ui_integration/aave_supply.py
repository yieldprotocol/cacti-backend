import re
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

from ...base import BaseSingleStepUIWorkflow, StepProcessingResult
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class AaveSupplyUIWorkflow(BaseSingleStepUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict):
        user_description = f"Supply {workflow_params['amount']} {workflow_params['token']} to Aave"
        self.__init__(self, wallet_chain_id, wallet_address, chat_message_id, workflow_type, workflow_params, user_description)

    def _goto_page_and_open_walletconnect(self, page):
        page.goto("https://app.aave.com/")
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()

    def _run_step(self, page, context) -> StepProcessingResult:
            # After WC is connected, wait for page to load user's profile
            page.get_by_text("Your supplies").wait_for()

            # Find token for an operation and click it
            try:
                page.locator("div").filter(
                    has_text=re.compile(
                        r"^{token}.*{operation}.*$".format(token=self.token, operation=self.operation))).get_by_role(
                    "button", name=self.operation).click()
            except PlaywrightTimeoutError:
                return StepProcessingResult(
                    status="error", error_msg=f"Token {self.token} not found on user's profile"
                )

            # Fill in the amount
            page.get_by_placeholder("0.00").fill(str(self.amount))

            page.locator("div").filter(has_text=re.compile(r"^ETH5,159\.242\.30%SupplyDetails$")).get_by_role("button", name="Supply").click()

            return StepProcessingResult(status="success")



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
