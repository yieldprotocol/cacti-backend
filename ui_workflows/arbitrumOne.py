from logging import basicConfig, INFO
import re

from .base import BaseUIWorkflow, handle_rpc_node_reqs, Page

basicConfig(level=INFO)


class ArbitrumOneUIWorkflow(BaseUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, token: str, operation: str, amount: float) -> None:
        super().__init__(wallet_chain_id, wallet_address)
        assert wallet_chain_id in (
            1, 42161), "only mainnet or arbitrum one supported"
        assert operation in ("Deposit"), operation
        self.token = token
        self.operation = operation
        self.amount = amount

    def _run_page(self, page):
        self._init_site(page)
        self._connect_wallet(page)

        # Trigger operation
        if self.operation == "Deposit":
            print('in deposit')

            # arbitrum one site doesn't seem to interpret what chain id we are connected with via WalletConnect,
            # so try to click on the network button in the ui
            if wallet_chain_id == 1:
                page.get_by_text('Switch to Mainnet').click()
            if wallet_chain_id == 42161:
                page.get_by_text('Switch to Arbitrum One').click()

            # TODO figure out if the below code works after resolving wallet connection issues

            # from_pattern = re.compile(r"*from:*", re.IGNORECASE)
            # arbi_pattern = re.compile(r"*arbitrum one*", re.IGNORECASE)
            # mainnet_pattern = re.compile(r"*mainnet*", re.IGNORECASE)

            # from_network_btn = page.get_by_text(
            #     from_pattern)

            # # select proper network button if not already chosen
            # if wallet_chain_id == 1 and not from_network_btn.text() == mainnet_pattern:
            #     # select "from: mainnet"
            #     page.get_by_text(from_pattern).click()
            #     page.get_by_role("listitem", name=mainnet_pattern).click()
            # elif wallet_chain_id == 42161 and not from_network_btn.text() == arbi_pattern:
            #     # select "from: arbitrum one"
            #     page.get_by_text(from_pattern).click()
            #     page.get_by_role("listitem", name=arbi_pattern).click()

            # # select token
            # if self.token != 'ETH':
            #     page.get_by_role("button", name="ETH").click()
            #     page.get_by_text(re.compile(
            #         f"*{self.token}*")).click()

            # # input amount
            # page.get_by_placeholder("Enter amount").fill(str(self.amount))

            # # submit
            # page.get_by_role("button", name=re.compile(
            #     "*move funds to*", re.IGNORECASE)).click()

        else:
            assert 0, f"unrecognized operation: {self.operation}"

        # Arbitrary wait to allow WC to relay info to our client
        page.wait_for_timeout(5000)

        result = self.stop_listener()
        assert result
        return result

    def _init_site(self, page: Page):
        page.goto("https://bridge.arbitrum.io/")

        # Intercept protocol's requests to its own RPC node
        page.route(
            "https://mainnet.infura.io/v3/8838d00c028a46449be87e666387c71a", handle_rpc_node_reqs)
        page.route("https://arb1.arbitrum.io/rpc", handle_rpc_node_reqs)

    def _connect_wallet(self, page: Page):
        # agree to terms
        page.get_by_text("Agree to terms").click()

        # connect
        page.get_by_text("Scan with WalletConnect to connect").click()
        page.get_by_text("Copy to clipboard").click()
        wc_uri = page.evaluate("() => navigator.clipboard.readText()")
        print(f"wc_uri: {wc_uri}")
        self.start_listener(wc_uri)


# Invoke this with python3 -m ui_workflows.arbitrumOne
if __name__ == "__main__":
    wallet_chain_id = 1
    wallet_address = "0x663ed57D834Cd1c2aB9D0B97305a64614a2CC3fd"
    token = "ETH"
    operation = "Deposit"
    amount = 0.1

    wf = ArbitrumOneUIWorkflow(
        wallet_chain_id, wallet_address, token, operation, amount)
    print(wf.run())
