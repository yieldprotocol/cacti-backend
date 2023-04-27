import threading
import time
import sys
from pywalletconnect.client import WCClient
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
import requests
from web3 import Web3
import argparse



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


def main(uri):
    pass




# Invoke this with python3 -m discovery.walletconnect
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--uri", type=str, help="walletconnect uri")
    args = parser.parse_args()

    if args.uri:
        # do something with the string_input
        print(args.uri)
        main(args.uri)
    else:
        print("No URI provided.")
        sys.exit()
    