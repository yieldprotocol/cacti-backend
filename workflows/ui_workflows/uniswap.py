import re
from logging import basicConfig, INFO

from .base import BaseUIWorkflow, handle_rpc_node_reqs, Result
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class UniswapUIWorkflow(BaseUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str,  swap_from_token: str, swap_to_token: str, operation: str, amount: float) -> None:
        swap_from_token = swap_from_token.upper()
        swap_to_token = swap_to_token.upper()
        description = f"Transaction on UNISWAP to {operation.lower()} {amount} {swap_from_token} {swap_to_token}"
        super().__init__(wallet_chain_id, wallet_address, description)
        assert operation in ("Swap", ), operation
        self.swap_from_token = swap_from_token 
        self.swap_to_token = swap_to_token
        self.operation = operation
        self.amount = amount
        self.is_approval_tx = False

    def connect_wallet(self, page):
        # Find connect wallet button and retrieve WC URI
        page.get_by_role("button", name="Connect Wallet").click()
        page.get_by_role("button", name="Icon WalletConnect").click()
        page.get_by_text("Copy to clipboard").click()
        wc_uri = page.evaluate("() => navigator.clipboard.readText()")

        self.start_listener(wc_uri)

    def _run_page(self, page):
        try:
            page.goto("https://app.uniswap.org/")

            # Intercept protocol's requests to its own RPC node
            page.route("https://mainnet.infura.io/v3/*", handle_rpc_node_reqs)

            # self.start_listener(wc_uri)
            page.get_by_role("link", name="Get started").click()
            self.connect_wallet(page)

            # # After WC is connected, wait for page to load 
            page.locator("#swap-page").get_by_text("Swap").wait_for()

            # Find and select swap_from_token
            if self.swap_from_token!="ETH":
                try:
                    page.get_by_role("button", name="ETH logo ETH").click()
                    page.get_by_placeholder("Search name or paste address").fill(self.swap_from_token)
                    try:
                        page.get_by_text(self.swap_from_token, exact=True).nth(1).click()
                    except PlaywrightTimeoutError:
                        page.get_by_text(self.swap_from_token, exact=True).click()
                except PlaywrightTimeoutError:
                    raise Exception(f"Token {self.swap_from_token} not found")
        
            # Find and select swap_to_token
            try:
                page.get_by_role("button", name="Select token").click()
                page.get_by_placeholder("Search name or paste address").fill(self.swap_to_token)
                try:
                    page.get_by_text(self.swap_to_token, exact=True).nth(1).click()
                except PlaywrightTimeoutError:
                    page.get_by_text(self.swap_to_token, exact=True).click()
            except PlaywrightTimeoutError:
                raise Exception(f"Token {self.swap_to_token} not found")
        
            # Fill the amount
            page.locator("#swap-currency-input").get_by_placeholder("0").click()
            page.locator("#swap-currency-input").get_by_placeholder("0").fill(str(self.amount))

            # Perform operation 
            try:
                page.get_by_role("button", name=self.operation).click()
            except PlaywrightTimeoutError:
                raise Exception(f"Insufficient balance to swap {self.amount}{self.swap_from_token} to {self.swap_to_token}")

            # confirm operation
            page.get_by_role("button", name=f"Confirm {self.operation}").click()

            # Arbitrary wait to allow WC to relay info to our client
            page.wait_for_timeout(5000)
            tx = self.stop_listener()
            self.is_approval_tx = True

            try:
                return Result(status="success", tx=tx[0], is_approval_tx=self.is_approval_tx, description=self.description)
            except:
                page.get_by_role("button", name="Dismiss").click()
                page.get_by_role("button", name="Transaction Settings").click()
                # page.get_by_placeholder("0.10").click()
                # page.get_by_placeholder("0.10").fill("1.0")
                page.get_by_role("button", name="Auto").click()
                page.get_by_role("button", name="Transaction Settings").click()
                self.connect_wallet(page)
                page.get_by_role("button", name=self.operation).click()
                page.get_by_role("button", name=f"Confirm {self.operation}").click()
                return Result(status="success", tx=tx[0], is_approval_tx=self.is_approval_tx, description=self.description)
        except Exception as e:
            self.stop_listener()
            return Result(status="error", error_msg=e.args[0], description=self.description)


# Invoke this with python3 -m ui_workflows.uniswap
if __name__ == "__main__":
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    wallet_address = "0x5f5326CF5304fDD5c0B1308911D183aEc274536A"

    swap_from_token = "ETH"
    swap_to_token = "UNI"
    operation = "Swap"
    amount = 0.01
    wf = UniswapUIWorkflow(wallet_chain_id, wallet_address, swap_from_token, swap_to_token, operation, amount)
    print(wf.run())
