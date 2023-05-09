import threading
import time
import sys
import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

import env
import requests
from utils import TENDERLY_FORK_URL
from pywalletconnect.client import WCClient
from playwright.sync_api import  sync_playwright, Page, BrowserContext


class BaseUIWorkflow(ABC):
    """Common interface for UI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, parsed_user_request: str, browser_storage_state: Optional[Dict] = None) -> None:
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = wallet_address
        self.parsed_user_request = parsed_user_request
        self.browser_storage_state = browser_storage_state
        self.thread = None
        self.result_container = []
        self.thread_event = threading.Event()
        self.is_approval_tx = False

    def run(self) -> Any:
        """Spin up headless browser and call run_page function on page."""
        print(f"Running UI workflow, {self.parsed_user_request}")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=_check_headless_allowed())
            context = browser.new_context(storage_state=self.browser_storage_state)
            context.grant_permissions(["clipboard-read", "clipboard-write"])
            page = context.new_page()

            if not env.is_prod():
                self._dev_mode_intercept_rpc(page)

            self._goto_page_and_open_walletconnect(page)
            self._connect_to_walletconnect_modal(page)

            ret = self._run_page(page, context)

            context.close()
            browser.close()
        print(f"UI workflow finished, {self.parsed_user_request}")
        return ret

    @abstractmethod
    def _run_page(self, page: Page, context: BrowserContext) -> Any:
        """Accept user input and return responses via the send_message function."""

    @abstractmethod
    def _goto_page_and_open_walletconnect(self,page):
        """Go to page and open walletconnect"""

    def _dev_mode_intercept_rpc(self, page) -> None:
        """Intercept RPC calls in dev mode"""
        page.route("**/*", self._intercept_rpc_node_reqs)

    def start_listener(self, wc_uri: str) -> None:
        assert self.thread is None, 'not expecting a thread to be started'
        self.thread = threading.Thread(
            target=wc_listen_for_messages,
            args=(self.thread_event, wc_uri, self.wallet_chain_id, self.wallet_address, self.result_container),
        )
        self.thread.start()

    def stop_listener(self) -> Any:
        if self.thread:
            self.thread_event.set()
            self.thread.join()
            self.thread = None
        if self.result_container:
            return self.result_container[-1]
        return None
    
    def _connect_to_walletconnect_modal(self, page):
        page.get_by_text("Copy to clipboard").click()
        wc_uri = page.evaluate("() => navigator.clipboard.readText()")
        self.start_listener(wc_uri)

    def _is_web3_call(self, request) -> Dict[bool, bool]:
        has_list_payload = False
        if request.post_data:
            try:
                payload = json.loads(request.post_data)
                obj_to_check = payload
                if isinstance(payload, list):
                    has_list_payload = True
                    obj_to_check = payload[0]

                if "method" in obj_to_check and obj_to_check["method"].startswith("eth_"):
                    return dict(is_web3_call=True, has_list_payload=has_list_payload)
            except Exception:
                pass
        return dict(is_web3_call=False, has_list_payload=has_list_payload)
    
    def _forward_rpc_node_reqs(self, route):
        route.continue_(url=TENDERLY_FORK_URL)

    def _handle_batch_web3_call(self, route):
        payload = json.loads(route.request.post_data)
        batch_result = []
        for obj in payload:
            response = requests.post(TENDERLY_FORK_URL, json=obj)
            response.raise_for_status()
            batch_result.append(response.json())
        route.fulfill(body=json.dumps(batch_result), headers={"access-control-allow-origin": "*", "access-control-allow-methods": "*", "access-control-allow-headers": "*"})

    def _intercept_rpc_node_reqs(self, route):
        result = self._is_web3_call(route.request)
        if result['is_web3_call']:
            if result['has_list_payload']:
                self._handle_batch_web3_call(route)                
            else:
                self._forward_rpc_node_reqs(route)
        else:
            route.continue_()


def wc_listen_for_messages(
        thread_event: threading.Event, wc_uri: str, wallet_chain_id: int, wallet_address: str, result_container: List):
    # Connect to WC URI using wallet address
    wclient = WCClient.from_wc_uri(wc_uri)
    print("Connecting with the Dapp ...")
    session_data = wclient.open_session()
    wclient.reply_session_request(session_data[0], wallet_chain_id, wallet_address)
    print("Wallet Connected.")

    print(" To quit : Hit CTRL+C, or disconnect from Dapp.")
    print("Now waiting for dapp messages ...")
    while not thread_event.is_set():
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
                    tx = read_data[2][0]
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

def _check_headless_allowed():
    # Headless cannot be used if on Mac, otherwise pyperclip doesn't work
    return sys.platform == 'linux'