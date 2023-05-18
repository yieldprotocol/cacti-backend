
# Always ensure decimals is set correctly for any token by checking the contract
MAINNET_TOKEN_TO_PROFILE_MAP = {
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
        if token == "ETH":
            return int(float(amount) * 10 ** 18)
        
        if token not in MAINNET_TOKEN_TO_PROFILE_MAP:
            raise Exception(f"Token {token} not supported by system")

        return int(float(amount) * 10 ** MAINNET_TOKEN_TO_PROFILE_MAP[token]["decimals"])
    else:
        raise Exception(f"Chain ID {chain_id} not supported by system")

def hexify_token_amount(chain_id: int, token: str, amount: str) -> str:
    return hex(parse_token_amount(chain_id, token, amount))