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

TENDERLY_FORK_BASE_URL = "https://rpc.tenderly.co/fork"

thread_event = threading.Event()
wallet_chain_id = 1 
wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" # vitalik.eth
result_container = []
fork_id = None # any default fork id will be set by the control panel
tenderly_fork_url = None

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
            request_id = read_data[0]
            method = read_data[1]
            parameters = read_data[2]

            print(f"WC data, id: {request_id}, method: {method}, params: {parameters}")
            if request_id is not None:
                print("\n <---- Received WalletConnect wallet query :")

                if method == "eth_sendTransaction":
                    # Get transaction params
                    tx = parameters[0]
                    print("TX:", tx)                    
                    tx_hash = tenderly_simulate_tx(wallet_address, tx)
                    wclient.reply(request_id, tx_hash)

                # Detect quit
                #  v1 disconnect
                if method == "wc_sessionUpdate" and parameters[0]["approved"] == False:
                    print("User disconnects from Dapp (WC v1).")
                    break
                #  v2 disconnect
                if method == "wc_sessionDelete" and parameters.get("message"):
                    print("User disconnects from Dapp (WC v2).")
                    print("Reason :", read_data[2]["message"])
                    break
        except KeyboardInterrupt:
            print("Demo interrupted.")
            break
        except Exception as e:
            # if an error occurs, it will be caught here
            print(f"An error occurred in walletConnect: {e}")
    wclient.close()
    print("WC disconnected.")

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
            # json_string = re.search(r'\{.*\}', request.post_data).group()

            # Parse JSON data into a Python dictionary
            payload = json.loads(request.post_data)
            if "method" in payload and payload["method"].startswith("eth_"):                
                print(f"Forwarded payload: '{request.post_data}'")
                return True
        except Exception as e:
            pass # Can be inferred as non-Web3 call
    return False

async def _async_forward_rpc_node_reqs(route):
    request = route.request
    data = json.loads(request.post_data)
    response = requests.post(tenderly_fork_url, json=data, headers=request.headers)
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

def tenderly_simulate_tx(wallet_address, tx):
    global tenderly_fork_url
    
    w3 = Web3(Web3.HTTPProvider(tenderly_fork_url))

    payload = {
    "id": 0,
    "jsonrpc": "2.0",
    "method": "eth_sendTransaction",
        "params": [
            {
            "from": wallet_address,
            "to": tx['to'],
            "value": tx['value'] if 'value' in tx else "0x0",
            "data": tx['data'],
            }
        ]
    }
    res = requests.post(tenderly_fork_url, json=payload)
    res.raise_for_status()

    tx_hash = res.json()['result']
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print("Tenderly TxHash:", tx_hash)

    if receipt['status'] == 0:
        raise Exception(f"Transaction failed, tx_hash: {tx_hash}, check Tenderly dashboard for more details")
    return tx_hash

async def main():
    global fork_id
    global tenderly_fork_url
    url = None
    zcontext = zmq.asyncio.Context()
    socket = zcontext.socket(zmq.REP)
    socket.bind("tcp://*:5558")
    
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
                    "id": fork_id
                }
                await socket.send_json(message)
            elif message["command"] == "ForkID":
                fork_id = message["id"]
                tenderly_fork_url = f"{TENDERLY_FORK_BASE_URL}/{fork_id}"
                await socket.send_string(f"New fork ID: {fork_id}") 
            elif message["command"] == "NewFork":
                fork_id = "124358929583"
                message = {
                    "id": fork_id
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