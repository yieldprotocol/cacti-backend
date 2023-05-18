import os
import json
from typing import Dict
from ..common import w3
from ..crypto_token import MAINNET_TOKEN_TO_PROFILE_MAP

ERC20_ABI = None


def load_erc20_abi():
    global ERC20_ABI
    with open(os.path.join(os.path.dirname(__file__), "./erc20.abi.json")) as f:
        ERC20_ABI = json.load(f)

def load_contract_abi(module_file_path: str, abi_relative_path: str) -> Dict:
    abi_abs_path = os.path.join(os.path.dirname(os.path.abspath(module_file_path)), abi_relative_path)
    with open(abi_abs_path, 'r') as f:
        return json.load(f)

def get_token_balance(token: str, wallet_address: str) -> int:
    """Get token balance of wallet address"""
    if token == "ETH":
        return w3.eth.get_balance(wallet_address)
    else:
        if token not in MAINNET_TOKEN_TO_PROFILE_MAP:
            raise Exception(f"Token {token} not supported by system")
        
        erc20_contract = w3.eth.contract(address=w3.to_checksum_address(MAINNET_TOKEN_TO_PROFILE_MAP[token]["address"]), abi=ERC20_ABI)
        return erc20_contract.functions.balanceOf(wallet_address).call()

load_erc20_abi()