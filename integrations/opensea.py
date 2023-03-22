import utils

# map Center to OpenSea
NETWORKS_MAP = {
    "ethereum-mainnet": "ethereum",
    "polygon-mainnet": "matic",
}


def fetch_nft_buy(network: str, address: str, token_id: str) -> str:
    network = NETWORKS_MAP.get(network, network)
    # TODO: for now, we just omit network altogether since frontend only works with ethereum
    return f"<|display-buy-nft({address},{token_id})|>"
