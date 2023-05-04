# Discovery

Discovery is a tool for loading a dApp website in a controlled environment for the purpose of discovering information about how it works. Discovery captures all web3 calls and routes them to a Tenderly fork. It also lets you connect to the app via walletConnect and captures all transactions that are created. The transactions are also forwarded to Tenderly. 

# Setup
1. `cd discovery`
1. `python3 -m venv "./.discovery-tool-venv"`
1. `source "./.discovery-tool-venv/bin/activate"`
1. `pip install -r requirements.txt`
1. `playwright install`

## Running 
Discovery consists of two scripts that need to run simultaneously:-
- control_panel.py - starts web page for sending user config actions to the Playwright framework's browser instance
- browser_runner.py - runs the Playwright framework's browser instance

To start the tool,
1. `cd discovery`
1. `source "./.discovery-tool-venv/bin/activate"`
1. `./start.sh`
