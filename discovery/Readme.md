# Discovery

Discovery is a tool for loading a dApp website in a controlled environment for the purpose of discovering information about how it works. Discovery captures all web3 calls and routes them to a Tenderly fork. It also lets you connect to the app via walletConnect and captures all transactions that are created. The transactions are also forwarded to Tenderly. 

# Setup
1. `cd discovery`
1. `python3 -m venv "./.discovery-tool-venv"`
1. `source "./.discovery-tool-venv/bin/activate"`
1. `pip install -r requirements.txt`
1. `playwright install`

# Running 
Discovery consists of two scripts that need to run simultaneously:-
- streamlit_control_panel.py - starts web page for sending user config actions to the Playwright framework's browser instance
- playwright_browser.py - runs the Playwright framework's browser instance

To start the tool,
1. `cd discovery`
1. `source "./.discovery-tool-venv/bin/activate"`
1. `./start.sh`

# How to use the tool
1. Run the tool by following above instructions, you should see 3 windows open up
    - "Playwright Control Panel" - this is the Streamlit-powered web page that configures the protocol URL, WalletConnect URI, Fork, etc. for the Playwright browser
    - "Playwright Inspector" - this is Playwright's window to allow user to record user actions and resume paused execution
    - "Chromium browser" - this browser is contorlled by Playwright
1. On the "Playwright Control Panel" page, enter the URL of the Protocol's UI and click "Open URL"
1. Initially the tool will be paused as it is started in debug mode, click the resume "arrow" button on the "Playwright Inspector" window to navigate to the page
1. The browser should now take you to the page and you will be able to interact with it
1. Before performing any protocol action, connect the test wallet by finding the connect button, getting the WalletConnect URI and pasting it in the "WalletConnect" field on the "Playwright Control Panel" page and then click "Start WC"
1. If you wan to record user actions, click the "record" button on the "Playwright Inspector" window
1. Interact with the Protocol UI normally by performing activities, transactions initiated will be auto-forwarded to Tenderly and instantly confirmed
1. When you are done interacting with the page, click the "Close" button at the bottom of the "Playwright Control Panel" page
1. You will be able to see the output of the tool in the `discovery/output` directory as described below

# Output
The output of the tool is stored in `discovery/output` under a directory derived from the the URL's hostname, the following are the files to expect:-
- {YYMMDD-HHMMSS}.log - contains the txs sent to Tenderly triggered by user actions and the corresponding simulation link to its dashboard
- trace_{YYMMDD-HHMMSS}.zip - Playwright's trace of the browser session that can be viewed this way https://playwright.dev/python/docs/trace-viewer#viewing-the-trace-1