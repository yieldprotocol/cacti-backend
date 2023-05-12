import re

from typing import Optional, Union, Literal

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ...base import StepProcessingResult 

FIVE_SECONDS = 5000
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