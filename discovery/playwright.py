import zmq
from playwright.sync_api import sync_playwright
from web3 import Web3
import json

# Set up the ZeroMQ context and socket
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")


TENDERLY_FORK_URL = "https://rpc.tenderly.co/fork/902db63e-9c5e-415b-b883-5701c77b3aa7"

def _is_web3_call(request):
    try:
        payload = json.loads(request.post_data)
        if "method" in payload and payload["method"].startswith("eth_"):
            return True
    except:
        pass
    return False

def _forward_rpc_node_reqs(route):
    route.continue_(url=TENDERLY_FORK_URL)

def _intercept_rpc_node_reqs(route):
    if _is_web3_call(route.request):
        _forward_rpc_node_reqs(route)
    else:
        route.continue_()


def main():
    # Set up Playwright
    with sync_playwright() as playwright:
        chromium = playwright.chromium
        browser = chromium.launch(headless = False)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
        context = browser.new_context(user_agent=user_agent)
        context.route("**/*",  _intercept_rpc_node_reqs)
        page = context.new_page()

        while True:
            # Wait for a message from the client
            message = socket.recv_string()

            # Perform the corresponding action based on the message
            if message == "Open Google":
                page.goto("https://www.google.com/")
                socket.send_string("Google opened successfully")
            elif message == "Exit":
                socket.send_string("Exiting")
                break
            else:
                socket.send_string("Unknown command")

        # Clean up
        browser.close()

    # Clean up ZeroMQ
    socket.close()
    context.term()

# Invoke this with: python3 -m discovery.playwright2
if __name__ == "__main__":
    main()