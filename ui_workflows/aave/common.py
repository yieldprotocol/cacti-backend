import re
import json
from typing import Optional, Union, Literal

import context
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from web3 import Web3

from utils import load_contract_abi
from ..base import StepProcessingResult, revoke_erc20_approval, set_erc20_allowance, TEST_WALLET_ADDRESS, USDC_ADDRESS

FIVE_SECONDS = 5000
AAVE_POOL_V3_PROXY_ADDRESS = Web3.to_checksum_address("0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2")
AAVE_WRAPPED_TOKEN_GATEWAY = Web3.to_checksum_address("0xd322a49006fc828f9b5b37ab215f99b4e5cab19c")

AAVE_SUPPORTED_TOKENS = [
    "ETH",
    "WETH",
    "USDC",
    "DAI",
    "USDT",
    "LINK",
    "AAVE",
    "LUSD",
    "CRV",
    "WBTC"
]


def get_aave_pool_v3_address_contract():
    web3_provider = context.get_web3_provider()
    return web3_provider.eth.contract(address=AAVE_POOL_V3_PROXY_ADDRESS, abi=load_contract_abi(__file__, "./abis/aave_pool_v3.abi.json"))

def get_aave_wrapped_token_gateway_contract():
    web3_provider = context.get_web3_provider()
    return web3_provider.eth.contract(address=AAVE_WRAPPED_TOKEN_GATEWAY, abi=load_contract_abi(__file__, "./abis/aave_wrapped_token_gateway.abi.json"))

class AaveMixin:
    def _goto_page_and_open_walletconnect(self, page):
        """Go to page and open WalletConnect modal"""
        page.goto("https://app.aave.com/")
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()

    def _find_and_fill_amount_helper(self, page, operation: Literal['Supply', 'Borrow']) -> Optional[StepProcessingResult]:
        # After WC is connected, wait for page to load user's profile
        page.get_by_text("Your supplies").wait_for()

        # Find token for an operation and click it
        try:
            regex =  r"^{token}.*{operation}Details$".format(token=self.token, operation=operation)
            page.locator("div").filter(has_text=re.compile(regex)).get_by_role("button", name=operation).click()
        except PlaywrightTimeoutError:
            return StepProcessingResult(
                status="error", error_msg=f"Token {self.token} not found on user's profile"
            )

        # Fill in the amount
        page.get_by_placeholder("0.00").fill(str(self.amount))
        return None

def aave_revoke_usdc_approval():
    revoke_erc20_approval(USDC_ADDRESS, TEST_WALLET_ADDRESS, AAVE_POOL_V3_PROXY_ADDRESS)

def aave_set_usdc_allowance(amount: int):
    set_erc20_allowance(USDC_ADDRESS, TEST_WALLET_ADDRESS, AAVE_POOL_V3_PROXY_ADDRESS, amount)

def aave_supply_eth_for_borrow_test():
    eth_to_supply = 1 * 10**18
    tx_hash = get_aave_wrapped_token_gateway_contract().functions.depositETH(AAVE_POOL_V3_PROXY_ADDRESS, TEST_WALLET_ADDRESS, 0).transact({'to': AAVE_WRAPPED_TOKEN_GATEWAY, 'value': hex(eth_to_supply), 'gas': '3C1F8'})
    receipt = context.get_web3_provider().eth.get_transaction_receipt(tx_hash)

def aave_set_eth_approval(amount: int):
    # https://docs.aave.com/developers/tokens/debttoken#approvedelegation
    print(f"Setting ETH approval")

    aave_variable_debt_eth_token_abi = [ { "inputs": [ { "internalType": "address", "name": "delegatee", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" } ], "name": "approveDelegation", "outputs": [], "stateMutability": "nonpayable", "type": "function" } ]
    aave_variable_debt_eth_token_address = Web3.to_checksum_address("0xea51d7853eefb32b6ee06b1c12e6dcca88be0ffe")
    aave_wrapped_token_gateway_address = Web3.to_checksum_address("0xd322a49006fc828f9b5b37ab215f99b4e5cab19c")

    web3_provider = context.get_web3_provider()

    contract = web3_provider.eth.contract(aave_variable_debt_eth_token_address, abi=json.dumps(aave_variable_debt_eth_token_abi))

    tx_hash = contract.functions.approveDelegation(aave_wrapped_token_gateway_address, amount).transact({'from': Web3.to_checksum_address(TEST_WALLET_ADDRESS), 'to': aave_variable_debt_eth_token_address, 'gas': "0x0"})

    tx_receipt = web3_provider.eth.wait_for_transaction_receipt(tx_hash)

def aave_revoke_eth_approval():
    # https://docs.aave.com/developers/tokens/debttoken#approvedelegation
    aave_set_eth_approval(0)

