from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union
import threading
import time
import sys

import requests
from pywalletconnect.client import WCClient
from playwright.sync_api import Playwright, sync_playwright, Page


class BaseUIWorkflow(ABC):
    """Common interface for UI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str):
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = wallet_address
        self.thread = None
        self.result_container = []

    @abstractmethod
    def run_page(self, page: Page) -> Any:
        """Accept user input and return responses via the send_message function."""

    def run(self) -> Any:
        """Spin up headless browser and call run_page function on page."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=_check_headless_allowed())
            context = browser.new_context()
            context.grant_permissions(["clipboard-read", "clipboard-write"])
            page = context.new_page()

            ret = self.run_page(page)

            context.close()
            browser.close()
        return ret

    def start_listener(self, wc_uri: str) -> None:
        assert self.thread is None, 'not expecting a thread to be started'
        self.thread = threading.Thread(
            target=wc_listen_for_messages,
            args=(wc_uri, self.wallet_chain_id, self.wallet_address, self.result_container),
        )
        self.thread.start()

    def stop_listener(self) -> Any:
        if self.thread:
            self.thread.join()
            self.thread = None
        if self.result_container:
            return self.result_container[-1]
        return None


def _check_headless_allowed():
    # Headless cannot be used if on Mac, otherwise pyperclip doesn't work
    return sys.platform == 'linux'


def handle_rpc_node_reqs(route, request):
    post_body = route.request.post_data
    # Forward request to Tenderly RPC node
    data = requests.post("https://rpc.tenderly.co/fork/902db63e-9c5e-415b-b883-5701c77b3aa7", data=post_body)
    route.fulfill(body=data.text)


def wc_listen_for_messages(wc_uri: str, wallet_chain_id: int, wallet_address: str, result_container: List):
    # Connect to WC URI using wallet address
    wclient = WCClient.from_wc_uri(wc_uri)
    print("Connecting with the Dapp ...")
    session_data = wclient.open_session()
    wclient.reply_session_request(session_data[0], wallet_chain_id, wallet_address)
    print("Wallet Connected.")

    print(" To quit : Hit CTRL+C, or disconnect from Dapp.")
    print("Now waiting for dapp messages ...")
    while True:
        try:
            time.sleep(0.3)
            # get_message return : (id, method, params) or (None, "", [])
            read_data = wclient.get_message()
            if read_data[0] is not None:
                print("\n <---- Received WalletConnect wallet query :")

                if (
                    read_data[1] == "eth_sendTransaction"
                ):
                    # Get transaction params
                    tx = read_data[2]
                    print("TX:", tx)
                    result_container.append(tx)
                    break

                # Detect quit
                #  v1 disconnect
                if (
                    read_data[1] == "wc_sessionUpdate"
                    and read_data[2][0]["approved"] == False
                ):
                    print("User disconnects from Dapp (WC v1).")
                    break
                #  v2 disconnect
                if read_data[1] == "wc_sessionDelete" and read_data[2].get("message"):
                    print("User disconnects from Dapp (WC v2).")
                    print("Reason :", read_data[2]["message"])
                    break
        except KeyboardInterrupt:
            print("Demo interrupted.")
            break
    wclient.close()
    print("WC disconnected.")
