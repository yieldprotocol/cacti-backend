import re

from typing import Optional, Union, Literal

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ...base import StepProcessingResult, revoke_erc20_approval, set_erc20_allowance, TEST_WALLET_ADDRESS, USDC_ADDRESS

FIVE_SECONDS = 5000
AAVE_POOL_V3_ADDRESS =  "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"

class AaveMixin:
    def _goto_page_and_open_walletconnect(self, page):
        """Go to page and open WalletConnect modal"""
        page.goto("https://app.aave.com/")
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()

    def _find_and_fill_amount_helper(self, page, operation: Literal['Supply', 'Borrow']) -> Optional[StepProcessingResult]:
        # After WC is connected, wait for page to load user's profile
        page.get_by_text("Your supplies").wait_for()

        # Find token for an operation and click it
        try:
            regex =  r"^{token}.*{operation}Details$".format(token=self.token, operation=operation)
            page.locator("div").filter(has_text=re.compile(regex)).get_by_role("button", name=operation).click()
        except PlaywrightTimeoutError:
            return StepProcessingResult(
                status="error", error_msg=f"Token {self.token} not found on user's profile"
            )

        # Fill in the amount
        page.get_by_placeholder("0.00").fill(str(self.amount))
        return None

def aave_revoke_usdc_approval():
    revoke_erc20_approval(USDC_ADDRESS, TEST_WALLET_ADDRESS, AAVE_POOL_V3_ADDRESS)

def aave_set_usdc_allowance(amount: int):
    set_erc20_allowance(USDC_ADDRESS, TEST_WALLET_ADDRESS, AAVE_POOL_V3_ADDRESS, amount)