import zmq
from playwright.sync_api import sync_playwright
from web3 import Web3
import json
import re
import os

import threading
import time
import sys
from pywalletconnect.client import WCClient
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
import requests
from web3 import Web3

import asyncio
from playwright.async_api import async_playwright
import zmq.asyncio

import concurrent.futures
executor = concurrent.futures.ThreadPoolExecutor()
thread = None
loop = asyncio.get_event_loop()


# Enable PWDEBUG to launch Inspector with the app
os.environ["PWDEBUG"] = "1"

# Set up the ZeroMQ context and socket
# zcontext = zmq.Context()
# socket = zcontext.socket(zmq.REP)
# socket.bind("tcp://*:5557")


thread_event = threading.Event()
wallet_chain_id = 1 
wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
result_container = []
forkID = "902db63e-9c5e-415b-b883-5701c77b3aa7"

TENDERLY_FORK_URL = "https://rpc.tenderly.co/fork/902db63e-9c5e-415b-b883-5701c77b3aa7"
tenderly_api_access_key = os.environ.get("TENDERLY_API_ACCESS_KEY", None)

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
        except Exception as e:
            # if an error occurs, it will be caught here
            print(f"An error occurred in walletConnect: {e}")
    wclient.close()
    print("WC disconnected.")

'''
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
'''

async def start_listener(wc_uri: str, thread_event: threading.Event, wallet_chain_id: int, wallet_address: str, result_container: List ) -> None:
    global thread
    if thread:
        await stop_listener()
        print("Thread already running!")
    thread = loop.run_in_executor(executor, wc_listen_for_messages, thread_event, wc_uri, wallet_chain_id, wallet_address, result_container)

async def stop_listener() -> Any:
    global thread
    if thread:
        thread_event.set()
        thread.result()  # This will block until the thread finishes.
        thread = None
    if result_container:
        return result_container[-1]
    return None



def _is_web3_call(request):
    if request.post_data:
        try:
            # Using regex to extract JSON data
            json_string = re.search(r'\{.*\}', request.post_data).group()

            # Parse JSON data into a Python dictionary
            payload = json.loads(json_string)
            # payload = json.loads(request.post_data)
            if "method" in payload and payload["method"].startswith("eth_"):
                ignore = ["eth_chainId", "eth_gasPrice", "eth_blockNumber"]
                if payload["method"] in ignore:
                    return False
                
                print(f"Forwarded payload: '{request.post_data}'")
                return True
        except Exception as e:
            print("An exception in web3 call occurred!")
            print(str(e))
    return False

async def _forward_rpc_node_reqs(route):
    print(f"Route forwarded to Tenderly: {route.request}")
    await route.continue_(url=TENDERLY_FORK_URL, headers={"X-Access-Key": tenderly_api_access_key})

async def _async_forward_rpc_node_reqs(route):
    request = route.request
    data = json.loads(request.post_data)
    response = requests.post(TENDERLY_FORK_URL, json=data, headers=request.headers)
    await route.fulfill(
        status=response.status_code,
        headers=dict(response.headers),
        body=response.content
    )



async def _intercept_rpc_node_reqs(route):
    if route.request.post_data and _is_web3_call(route.request):
        print(f"Forwarding:{route.request.url}")
        await _async_forward_rpc_node_reqs(route)
    else:
        # print(f'Request URL: {route.request.url}')
        # print(f'Request Headers: {route.request.headers}')
        # print(f'Request Post Data: {route.request.post_data}')
        print(f"Continuing:{route.request.url}")
        await route.continue_()

async def main():
    global forkID
    global TENDERLY_FORK_URL
    url = None
    zcontext = zmq.asyncio.Context()
    socket = zcontext.socket(zmq.REP)
    socket.bind("tcp://*:5558")

    # Define a flag to track request interception
    is_intercepting = False


    # Set up Playwright
    async with async_playwright() as playwright:
        chromium = playwright.chromium
        browser = await chromium.launch(headless = False)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()
        # await context.tracing.start(name='trace', screenshots=True, snapshots=True)

        def print_console_msg(msg):
            print(msg.text)

        page.on("console", print_console_msg)
        while True:
            # Wait for a message from the client
            message = await socket.recv_json()

            # Perform the corresponding action based on the message
            if message["command"] == "Open":
                url = message["url"]
                print(f"Received URL: {url}")
                await page.goto(url)
                await socket.send_string("Website opened successfully")    
            elif message["command"] == "WC":
                wc = message["wc"]
                if thread:
                    await stop_listener()
                await start_listener(
                    wc, 
                    thread_event, 
                    wallet_chain_id, 
                    wallet_address, 
                    result_container 
                )
                await socket.send_string("WalletConnect started")    
            elif message["command"] == "GetForkID":
                message = {
                    "id": forkID
                }
                await socket.send_json(message)
            elif message["command"] == "ForkID":
                forkID = message["id"]
                TENDERLY_FORK_URL = f"https://rpc.tenderly.co/fork/{forkID}"
                await socket.send_string(f"New fork ID: {forkID}") 
            elif message["command"] == "NewFork":
                forkID = "124358929583"
                message = {
                    "id": forkID
                }
                await socket.send_json(message)
            elif message["command"] == "Forward":
                await context.route("**/*",  _intercept_rpc_node_reqs)
                await socket.send_string("Forwarding Started") 
            elif message["command"] == "endForward":
                await context.unroute("**/*",  _intercept_rpc_node_reqs)
                await socket.send_string("Forwarding Ended") 
            elif message["command"] == "Exit":
                await socket.send_string("Exiting")
                break
            else:
                await socket.send_string("Unknown command")

        # Stop trace
        # await context.tracing.stop(path='trace.zip')
        # Clean up
        await browser.close()
    # close walletconnect
    stop_listener()

    # Clean up ZeroMQ
    socket.close()
    zcontext.term()


# Invoke this with: python3 -m discovery.a_playwright
if __name__ == "__main__":
    asyncio.run(main())