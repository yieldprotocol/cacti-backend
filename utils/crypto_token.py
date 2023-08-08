from typing import Dict, Optional

from web3 import Web3

from .abi import ERC20_ABI

# Always ensure decimals is set correctly for any token by checking the contract
MAINNET_TOKEN_TO_PROFILE_MAP = {
    "ETH": {
        "address": "",
        "decimals": 18,
    },
    "WETH": {
        "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "decimals": 18,
    },
    "USDC": { 
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "decimals": 6,
    },
    "DAI": { 
        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "decimals": 18,
    },
    "USDT": { 
        "address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "decimals": 6
    },
    "LINK": { 
        "address": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
        "decimals": 18
    },
    "AAVE": { 
        "address": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "decimals": 18
    },
    "LUSD": { 
        "address" : "0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",
        "decimals": 18
    },
    "CRV": { 
        "address": "0xd533a949740bb3306d119cc777fa900ba034cd52",
        "decimals": 18
    },
    "WBTC": {
        "address": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
        "decimals": 8
    },
}

def parse_token_amount(chain_id: int, token: str, amount: str) -> int:
    if chain_id == 1:
        return _mainnet_parse_token_amount(token, amount)
    else:
        raise Exception(f"Chain ID {chain_id} not supported by system")

def hexify_token_amount(chain_id: int, token: str, amount: str) -> str:
    return hex(parse_token_amount(chain_id, token, amount))

def get_token_balance(web3_provider: Web3, chain_id: int, token: str, wallet_address: str) -> int:
    if chain_id == 1:
        return _mainnet_token_balance(web3_provider, token, wallet_address)
    else:
        raise Exception(f"Chain ID {chain_id} not supported by system")
    
def format_token_balance(chain_id: int, token: str, amount: int) -> str:
    if chain_id == 1:
        decimals = _mainnet_get_token_profile(token)["decimals"]
        return str(amount / 10 ** decimals)
    else:
        raise Exception(f"Chain ID {chain_id} not supported by system")

def has_sufficient_erc20_allowance(web3_provider: Web3, chain_id: int, token: str, wallet_address: str, spender_address: str, amount: str) -> bool:
    if chain_id == 1:
        erc20_contract = web3_provider.eth.contract(address=get_token_address(chain_id, token), abi=ERC20_ABI)
        return erc20_contract.functions.allowance(wallet_address, spender_address).call() >= _mainnet_parse_token_amount(token, amount)
    else:
        raise Exception(f"Chain ID {chain_id} not supported by system")

def generate_erc20_approve_encoded_data(web3_provider: Web3, chain_id: int, token: str, spender_address: str, amount: str) -> Dict:
    if chain_id == 1:
        erc20_contract = web3_provider.eth.contract(address=get_token_address(chain_id, token), abi=ERC20_ABI)
        return erc20_contract.encodeABI(fn_name="approve", args=[web3_provider.to_checksum_address(spender_address), _mainnet_parse_token_amount(token, amount)])
    else:
        raise Exception(f"Chain ID {chain_id} not supported by system")

def get_token_address(chain_id: int, token: str) -> str:
    if chain_id == 1:
        return _mainnet_get_token_address(token)
    else:
        raise Exception(f"Chain ID {chain_id} not supported by system")

def _mainnet_parse_token_amount(token: str, amount: str) -> int:
    if token == "ETH":
        return int(float(amount) * 10 ** 18)

    return int(float(amount) * 10 ** _mainnet_get_token_profile(token)["decimals"])

def _mainnet_token_balance(web3_provider: Web3, token: str, wallet_address: str) -> int:
    if token == "ETH":
        return web3_provider.eth.get_balance(wallet_address)
    else:        
        erc20_contract = web3_provider.eth.contract(address=_mainnet_get_token_address(token), abi=ERC20_ABI)
        return erc20_contract.functions.balanceOf(wallet_address).call()

def _mainnet_get_token_profile(token: str) -> Dict:
    if token not in MAINNET_TOKEN_TO_PROFILE_MAP:
        raise Exception(f"Token {token} not supported by system")
    return MAINNET_TOKEN_TO_PROFILE_MAP[token]

def _mainnet_get_token_address(token: str) -> str:
    if token == "ETH":
        raise Exception("ETH does not have an address")
    
    return Web3.to_checksum_address(_mainnet_get_token_profile(token)["address"])