from logging import basicConfig, INFO

from .base import BaseUIWorkflow

basicConfig(level=INFO)


class AaveUIWorkflow(BaseUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, token: str, operation: str, amount: float) -> None:
        super().__init__(wallet_chain_id, wallet_address)
        assert operation in ("Supply", "Borrow"), operation
        self.token = token
        self.operation = operation
        self.amount = amount

    def _run_page(self, page):
        page.goto("https://app.aave.com/")

        # Intercept protocol's requests to its own RPC node
        page.route("https://eth-mainnet.gateway.pokt.network/**/*", handle_rpc_node_reqs)
        page.route("https://rpc.ankr.com/**/*", handle_rpc_node_reqs)

        # Find connect wallet button and retrieve WC URI
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()
        page.get_by_text("Copy to clipboard").click()
        wc_uri = page.evaluate("() => navigator.clipboard.readText()")

        self.start_listener(wc_uri)

        # Trigger operation
        if self.operation == "Supply":
            page.get_by_text(self.token, exact=True).first.click()
            page.get_by_role("button", name=self.token, exact=True).click()
        elif self.operation == "Borrow":
            page.get_by_role("link", name=self.token).click()
        else:
            assert 0, f"unrecognized operation: {self.operation}"
        page.get_by_role("button", name=self.operation).click()
        page.get_by_placeholder("0.00").fill(str(self.amount))
        page.get_by_role("button", name=f"{self.operation} {self.token}").click()

        # Arbitrary wait to allow WC to relay info to our client
        page.wait_for_timeout(5000)

        result = self.stop_listener()
        assert result
        return result


# Invoke this with python3 -m ui_workflows.aave

if __name__ == "__main__":
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    wallet_address = "0x5f5326CF5304fDD5c0B1308911D183aEc274536A"
    token = "ETH"
    operation = "Supply"
    amount = 0.1
    #wf = AaveUIWorkflow(wallet_chain_id, wallet_address, token, operation, amount)
    #print(wf.run())

    token = "USDC"
    operation = "Borrow"
    amount = 0.1
    wf = AaveUIWorkflow(wallet_chain_id, wallet_address, token, operation, amount)
    print(wf.run())
