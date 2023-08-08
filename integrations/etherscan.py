import requests

from utils import ETHERSCAN_API_KEY, w3


def get_ABI(contract_address):
    url = f'https://api.etherscan.io/api?module=contract&action=getabi&address={contract_address}&apikey={ETHERSCAN_API_KEY}'
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()['result']
    return result


erc_20_abi = get_ABI("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")


TOKEN_TO_CONTRACT_ADDRESS = {
    'ETH': '0x0000000000000000000000000000000000000000',
    'USDT': '0xdac17f958d2ee523a2206206994597c13d831ec7',
    'USDC': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
    'DAI': '0x6b175474e89094c44da98b954eedeac495271d0f',
    'LINK': '0x514910771af9ca656af840dff83e8264ecf986ca',
    'UNI': '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984',
    'WBTC': '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',
    'AAVE': '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9',
    'MKR': '0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2',
}


def get_contract_address(token):
    contract_address = TOKEN_TO_CONTRACT_ADDRESS.get(token.upper())
    return contract_address


def is_zero_address(address):
    return address == '0x0000000000000000000000000000000000000000'


def get_all_transactions(address):
    # Construct the Etherscan API URL
    url = f'https://api.etherscan.io/api?module=account&action=getabi&address={address}&apikey={ETHERSCAN_API_KEY}'
    # Make the GET request
    response = requests.get(url)
    response.raise_for_status()
    # Parse the response
    data = response.json()
    return data


def get_all_eth_from_address(address):
    # Construct the Etherscan API URL
    url = f'https://api.etherscan.io/api?module=account&action=txlist&address={address}&apikey={ETHERSCAN_API_KEY}&sort=desc'
    # Make the GET request
    response = requests.get(url)
    response.raise_for_status()
    # Parse the response
    data = response.json()
    transactions = data['result']
    value = 0
    for trans in transactions:
        if trans['from'].lower() == address.lower():
            value += int(trans['value'])
    return value


def get_all_eth_to_address(address):
    # Construct the Etherscan API URL
    url = f'https://api.etherscan.io/api?module=account&action=txlist&address={address}&apikey={ETHERSCAN_API_KEY}&sort=desc'
    # Make the GET request
    response = requests.get(url)
    response.raise_for_status()
    # Parse the response
    data = response.json()
    transactions = data['result']
    value = 0
    for trans in transactions:
        if trans['to'].lower() == address.lower():
            value += int(trans['value'])
    return value


def get_all_gas_for_address(address):
    # Construct the Etherscan API URL
    url = f'https://api.etherscan.io/api?module=account&action=txlist&address={address}&apikey={ETHERSCAN_API_KEY}&sort=desc'
    # Make the GET request
    response = requests.get(url)
    # Parse the response
    data = response.json()
    transactions = data['result']
    value = 0
    for trans in transactions:
        value += int(trans['gas'])
    return value


def get_token_transfer_history(token_address, address):
    # Construct the Etherscan API URL
    url = f'https://api.etherscan.io/api?module=account&action=tokentx&address={address}&contractaddress={token_address}&apikey={ETHERSCAN_API_KEY}&sort=desc'
    # Make the GET request
    response = requests.get(url)
    response.raise_for_status()
    # Parse the response
    data = response.json()
    transactions = data['result']
    return transactions


def get_token_transfer_history_to_address(token_address, address):
    transactions = get_token_transfer_history(token_address, address)
    result = []
    for trans in transactions:
        if trans['to'].lower() == address.lower():
            result.append(trans)
    return result


def get_token_transfer_history_from_address(token_address, address):
    transactions = get_token_transfer_history(token_address, address)
    result = []
    for trans in transactions:
        if trans['from'].lower() == address.lower():
            result.append(trans)
    return result


def get_total_token_transfer_history_to_address(token_address, address):
    transactions = get_token_transfer_history_to_address(token_address,
                                                          address)
    value = 0
    for trans in transactions:
        value += int(trans['value'])
    return value


def get_total_token_transfer_history_from_address(token_address, address):
    transactions = get_token_transfer_history_from_address(token_address,
                                                            address)
    value = 0
    for trans in transactions:
        value += int(trans['value'])
    return value

def get_nft_transfer_history(token_address, address):
    # Construct the Etherscan API URL
    url = f'https://api.etherscan.io/api?module=account&action=tokennfttx&address={address}&contractaddress={token_address}&apikey={ETHERSCAN_API_KEY}&sort=desc'
    # Make the GET request
    response = requests.get(url)
    response.raise_for_status()
    # Parse the response
    data = response.json()
    transactions = data['result']
    return transactions

def get_nft_transfer_history_to_address(token_address, address):
    transactions = get_nft_transfer_history(token_address, address)
    result = []
    for trans in transactions:
        if trans['to'].lower() == address.lower():
            result.append(trans)
    return result

def get_nft_transfer_history_from_address(token_address, address):
    transactions = get_nft_transfer_history(token_address, address)
    result = []
    for trans in transactions:
        if trans['from'].lower() == address.lower():
            result.append(trans)
    return result
