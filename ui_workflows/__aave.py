import re
from logging import basicConfig, INFO

from .base import BaseUIWorkflow, Result
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class AaveUIWorkflow(BaseUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, token: str, operation: str, amount: float) -> None:
        token = token.upper()
        parsed_user_request = f"{operation.capitalize()} {amount} {token} on AAVE"
        super().__init__(wallet_chain_id, wallet_address, parsed_user_request)
        assert operation in ("Supply", "Borrow", "Repay", "Withdraw"), operation
        self.token = token
        self.operation = operation
        self.amount = amount
        self.is_approval_tx = False

    def _goto_page_and_open_walletconnect(self, page):
        page.goto("https://app.aave.com/")
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()

    def _run_page(self, page, context):
        try:
            # After WC is connected, wait for page to load user's profile
            page.get_by_text("Your supplies").wait_for()

            # Find token for an operation and click it
            try:
                page.locator("div").filter(
                    has_text=re.compile(
                        r"^{token}.*{operation}.*$".format(token=self.token, operation=self.operation))).get_by_role(
                    "button", name=self.operation).click()
            except PlaywrightTimeoutError:
                raise Exception(f"Token {self.token} not found")

            # Fill in the amount
            page.get_by_placeholder("0.00").fill(str(self.amount))

            # If non-ETH token, check for approval
            if self.operation == "Withdraw" or (self.operation in ["Supply", "Repay"] and self.token != "ETH"):
                try:
                    page.get_by_role("button", name="Approve").click()
                    self.is_approval_tx = True
                except PlaywrightTimeoutError:
                    # If timeout error, assume approval given
                    page.get_by_role("button", name=self.operation).click()
            else:
                page.get_by_role("button", name=self.operation).click()

            # Arbitrary wait to allow WC to relay info to our client
            page.wait_for_timeout(5000)
            tx = self.stop_listener()

            if self.is_approval_tx:
                description = f"Approval transaction on AAVE to {self.operation.lower()} {self.amount} {self.token}"
            else:
                description = f"Transaction on AAVE to {self.operation.lower()} {self.amount} {self.token}"

            return Result(
                status="success", tx=tx,
                is_approval_tx=self.is_approval_tx, parsed_user_request=self.log_params,
                description=description)
        except Exception as e:
            self.stop_listener()
            return Result(
                status="error", error_msg=e.args[0],
                parsed_user_request=self.log_params, description=self.log_params)


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
