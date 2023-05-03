# Discovery

Discovery is a tool for loading a dApp website in a controlled environment for the purpose of discovering information about how it works. Discovery captures all web3 calls and routes them to a Tenderly fork. It also lets you connect to the app via walletConnect and captures all transactions that are created. The transactions are also forwarded to Tenderly. 

## Running 

Discovery consists of two scripts "streamlit.py" and "playwright.py". You will need to run both. 

First start playwright.py
'''
python3 -m discovery.a_playwright
'''

then launch
'''
streamlit run ./discovery/streamlit.py
'''

## Using Playwright Inspect  with Discovery

You can launch Playwright Inspect along with Discovery for recording interactions with a page. To do so, uncomment the following line in a_playwright:
'''
os.environ["PWDEBUG"] = "1"
'''

Please note that Inspect defaults to debugging the "a_playwright.py" script, and so you will need to step over the current breakpoint to load a page and start recording interactions. 
