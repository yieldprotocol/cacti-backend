import pyperclip
from logging import basicConfig, INFO

import registry
from .base import BaseUIWorkflow

basicConfig(level=INFO)


@registry.register_class
class AaveUIWorkflow(BaseUIWorkflow):

    def run_page(self, page):
        page.goto("https://app.aave.com/")

        # Intercept protocol's requests to its own RPC node
        page.route("https://eth-mainnet.gateway.pokt.network/**/*", handle_rpc_node_reqs)
        page.route("https://rpc.ankr.com/**/*", handle_rpc_node_reqs)

        # Find connect wallet button and retrieve WC URI
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()
        page.get_by_text("Copy to clipboard").click()
        wc_uri = pyperclip.paste()

        self.start_listener(wc_uri)

        # Supply/Lend 0.1 ETH
        page.get_by_text("ETH", exact=True).first.click()
        page.get_by_role("button", name="ETH", exact=True).click()
        page.get_by_role("button", name="Supply").click()
        page.get_by_placeholder("0.00").fill("0.1")
        page.get_by_role("button", name="Supply ETH").click()

        # Arbitrary wait to allow WC to relay info to our client
        page.wait_for_timeout(5000)

        result = self.stop_listener()
        assert result
        return result


if __name__ == "__main__":
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    wallet_address = "0x5f5326CF5304fDD5c0B1308911D183aEc274536A"
    wf = AaveUIWorkflow(wallet_chain_id, wallet_address)
    print(wf.run())
