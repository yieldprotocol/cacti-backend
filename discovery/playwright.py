import zmq
from playwright.sync_api import sync_playwright
from web3 import Web3
import json

import threading
import time
import sys
from pywalletconnect.client import WCClient
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
import requests
from web3 import Web3


# Set up the ZeroMQ context and socket
zcontext = zmq.Context()
socket = zcontext.socket(zmq.REP)
socket.bind("tcp://*:5555")
thread=None

thread_event = threading.Event()
wallet_chain_id = 1 
wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
result_container = []

TENDERLY_FORK_URL = "https://rpc.tenderly.co/fork/902db63e-9c5e-415b-b883-5701c77b3aa7"

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
                print(read_data[0])
        except KeyboardInterrupt:
            print("Demo interrupted.")
            break
    wclient.close()
    print("WC disconnected.")


def start_listener(wc_uri: str, thread_event: threading.Event, wallet_chain_id: int, wallet_address: str, result_container: List ) -> None:
    global thread
    if thread:
        stop_listener()
        print("Thread already running!")
    thread = threading.Thread(
        target=wc_listen_for_messages,
        args=(thread_event, wc_uri, wallet_chain_id, wallet_address, result_container),
    )
    thread.start()

def stop_listener() -> Any:
    global thread
    if thread:
        thread_event.set()
        thread.join()
        thread = None
    if result_container:
        return result_container[-1]
    return None

def _is_web3_call(request):
    if request.post_data:
        try:
            payload = json.loads(request.post_data)
            if "method" in payload and payload["method"].startswith("eth_"):
                return True
        except Exception as e:
            print("An exception in web3 call occurred!")
            print(str(e))
    return False

def _forward_rpc_node_reqs(route):
    # print(f"Route forwarded to Tenderly: {route.request}")
    route.continue_(url=TENDERLY_FORK_URL)

def _intercept_rpc_node_reqs(route):
    if _is_web3_call(route.request):
        _forward_rpc_node_reqs(route)
    else:
        # print(f'Request URL: {route.request.url}')
        # print(f'Request Headers: {route.request.headers}')
        # print(f'Request Post Data: {route.request.post_data}')
        route.continue_()


def main():
    url = None
    # Set up Playwright
    with sync_playwright() as playwright:
        chromium = playwright.chromium
        browser = chromium.launch(headless = False)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
        context = browser.new_context(user_agent=user_agent)
        context.route("**/*",  _intercept_rpc_node_reqs)
        page = context.new_page()

        def print_console_msg(msg):
            print(msg.text)

        page.on("console", print_console_msg)
        while True:
            # Wait for a message from the client
            message = socket.recv_json()

            # Perform the corresponding action based on the message
            if message["command"] == "Open":
                url = message["url"]
                print(f"Received URL: {url}")
                page.goto(url)
                socket.send_string("Website opened successfully")    
            elif message["command"] == "WC":
                wc = message["wc"]
                start_listener(
                    wc, 
                    thread_event, 
                    wallet_chain_id, 
                    wallet_address, 
                    result_container 
                )
                socket.send_string("WalletConnect started")    
            elif message["command"] == "Exit":
                socket.send_string("Exiting")
                break
            else:
                socket.send_string("Unknown command")

        # Clean up
        browser.close()
    # close walletconnect
    stop_listener()

    # Clean up ZeroMQ
    socket.close()
    zcontext.term()


# Invoke this with: python3 -m discovery.playwright
if __name__ == "__main__":
    main()