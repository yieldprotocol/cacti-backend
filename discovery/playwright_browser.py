import zmq
from playwright.sync_api import sync_playwright
from web3 import Web3
import json
import re
import os
import logging

import threading
import time
import sys
from datetime import datetime
from urllib.parse import urlparse

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
output_dir = "./output"
formatted_start_time = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
file_logger = logging.getLogger('file_logger')
file_logger.setLevel(logging.INFO)

# Enable PWDEBUG to launch Inspector with the app
os.environ["PWDEBUG"] = "1"

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

            # print(f"WC data, id: {request_id}, method: {method}, params: {parameters}")
            if request_id is not None:
                print("\n <---- Received WalletConnect wallet query :")

                if method == "eth_sendTransaction":
                    # Get transaction params
                    tx = parameters[0]
                    print("WC msg, tx=", tx)                    
                    tx_hash = tenderly_simulate_tx(wallet_address, tx)
                    wclient.reply(request_id, tx_hash)

                # Detect quit
                #  v1 disconnect
                if method == "wc_sessionUpdate" and parameters[0]["approved"] == False:
                    print("WC msg, uer disconnects from Dapp (WC v1).")
                    break
                #  v2 disconnect
                if method == "wc_sessionDelete" and parameters.get("message"):
                    print("WC msg, user disconnects from Dapp (WC v2).")
                    print("WC msg, reason :", read_data[2]["message"])
                    break
        except KeyboardInterrupt:
            print("WC handler, demo interrupted.")
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

async def stop_listener():
    global thread
    if thread:
        thread_event.set()
        thread = None

def _is_web3_call(request: str):
    if request.post_data:
        try:
            # Using regex to extract JSON data
            # json_string = re.search(r'\{.*\}', request.post_data).group()

            # Parse JSON data into a Python dictionary
            payload = json.loads(request.post_data)
            if "method" in payload and payload["method"].startswith("eth_"):                
                # print(f"Forwarded payload: '{request.post_data}'")
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
        # print(f"Forwarding:{route.request.url}")
        await _async_forward_rpc_node_reqs(route)
    else:
        # print(f"Continuing:{route.request.url}")
        await route.continue_()

def tenderly_simulate_tx(wallet_address, tx):
    global tenderly_fork_url
    
    w3 = Web3(Web3.HTTPProvider(tenderly_fork_url))

    send_tx_payload = {
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
    res = requests.post(tenderly_fork_url, json=send_tx_payload)
    res.raise_for_status()

    tx_hash = res.json()['result']

    get_latest_tx_payload = {
        "jsonrpc": "2.0",
        "method": "evm_getLatest",
        "params": []
    }

    res = requests.post(tenderly_fork_url, json=get_latest_tx_payload)
    res.raise_for_status()

    tenderly_simulation_id = res.json()['result']

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    tenderly_link = f"https://dashboard.tenderly.co/Yield/chatweb3/fork/{fork_id}/simulation/{tenderly_simulation_id}"

    if receipt['status'] == 0:
        file_logger.info(f"Tx failed, tx_hash: {tx_hash}, tenderly_link: {tenderly_link}")
    else:
        file_logger.info(f"Tx successful, tx_hash: {tx_hash}, tenderly_link: {tenderly_link}")

    return tx_hash


def create_output_dir(app_url: str):
    global output_dir
    parsed_url = urlparse(app_url)
    host = parsed_url.hostname.replace(".", "_")

    dir_name = f"./output/{host}"

    current_dir = os.path.dirname(os.path.abspath(__file__))

    output_dir = os.path.join(current_dir, dir_name)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

def setup_file_logger():
    global output_dir
    global formatted_start_time

    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = f"{formatted_start_time}.log"
    file_path = os.path.join(current_dir, f"{output_dir}/{file_name}")

    file_handler = logging.FileHandler(file_path)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    file_logger.addHandler(file_handler)


async def main():
    global fork_id
    global tenderly_fork_url
    global formatted_start_time

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
        await context.tracing.start(name='trace', screenshots=True, snapshots=True)

        page = await context.new_page()

        def print_console_msg(msg):
            print(msg.text)

        page.on("console", print_console_msg)
        while True:
            # Wait for a message from the client
            message = await socket.recv_json()

            # Perform the corresponding action based on the message
            if message["command"] == "Open":
                formatted_start_time = datetime.now().strftime('%y%m%d-%H%M%S')
                url = message["url"]
                
                print(f"Received URL: {url}")
                
                await page.goto(url)
                await socket.send_string("Website opened successfully")    
                
                create_output_dir(url)
                setup_file_logger()

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
                break
            else:
                await socket.send_string("Unknown command")

        # Clean up
        # Stop trace
        await context.tracing.stop(path=f"{output_dir}/trace_{formatted_start_time}.zip")
        await browser.close()
    # close walletconnect
    await stop_listener()

    await socket.send_string("Performed cleanup, about to shutdown Playwright browser")
    # Clean up ZeroMQ
    socket.close()
    zcontext.term()

# Invoke this with: python3 -m discovery.a_playwright
if __name__ == "__main__":
    asyncio.run(main())