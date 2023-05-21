from web3 import Web3
from .common import TENDERLY_FORK_URL
import env

CHAIN_ID_TO_PROD_RPC_URL = {
    "1": "https://mainnet.infura.io/v3/YOUR_INFURA_API_KEY_GOES_HERE"  # TODO: this is for mainnet to be updated when we go live
}

CHAIN_ID_TO_TEST_RPC_URL = {"1": TENDERLY_FORK_URL}


def get_web3_from_chain_id(chain_id: str) -> Web3:
    if CHAIN_ID_TO_PROD_RPC_URL.get(chain_id) is None:
        raise Exception(f"Chain ID {chain_id} not supported")

    if env.is_prod():
        rpc_url = CHAIN_ID_TO_PROD_RPC_URL[chain_id]
    else:
        rpc_url = CHAIN_ID_TO_TEST_RPC_URL[chain_id]
    return Web3(Web3.HTTPProvider(rpc_url))


def get_web3_from_fork_id(fork_id: str) -> Web3:
    rpc_url = get_fork_url(fork_id)
    return Web3(Web3.HTTPProvider(rpc_url))


def get_fork_url(fork_id: str) -> str:
    return f"https://rpc.tenderly.co/fork/{fork_id}"