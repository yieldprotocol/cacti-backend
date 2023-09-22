from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import requests
from web3 import Web3

from urllib.parse import urlencode
from gpt_index.utils import ErrorToRetry, retry_on_exceptions_with_backoff

import utils
from chat.container import ContainerMixin, dataclass_to_container_params


HEADERS = {
    "accept": "application/json",
    "X-API-Key": utils.OPENSEA_API_KEY,
}
# map Center to OpenSea
NETWORKS_MAP = {
    "ethereum-mainnet": "ethereum",
    "polygon-mainnet": "matic",
}
API_V1_URL = "https://api.opensea.io/api/v1"
API_V2_URL = "https://api.opensea.io/v2"
MAX_RESULTS = 100
PAGE_LIMIT = 100

# this represents an NFT collection
@dataclass
class NFTContract:
    chain: str
    address: str
    slug: str


# this is a listing of an NFT asset
@dataclass
class NFTListing:
    chain: str
    address: str
    token_id: str
    price_str: str
    price_value: int
    order_hash: Optional[str] = None
    protocol_address: Optional[str] = None
    expiration_time: Optional[int] = None

@dataclass
class NFTFulfillmentData:
    parameters: Dict[str, Any]
    signature: str
    value_amount: int


def fetch_contract(address: str) -> NFTContract:
    """Fetch data about a contract (collection)."""
    url = f"{API_V2_URL}/chain/ethereum/contract/{address}/nfts"

    def _exec_request():
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()

    obj = retry_on_exceptions_with_backoff(
        _exec_request,
        [ErrorToRetry(requests.exceptions.HTTPError, _should_retry_exception)],
    )
    return NFTContract(
        chain='ethereum',
        address=address,
        slug=obj["nfts"][0]["collection"],
    )

def fetch_listings(address: str, token_id: str) -> List[NFTListing]:
    """Fetch cheapest listing for an asset."""
    chain = "ethereum"
    limit = 1
    ret = []
    q = urlencode(dict(
        limit=limit,
        asset_contract_address=address,
        token_ids=token_id,
        order_by='eth_price',
        order_direction='asc'
    ))
    url = f"{API_V2_URL}/orders/{chain}/seaport/listings?{q}"

    def _exec_request():
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()

    obj = retry_on_exceptions_with_backoff(
        _exec_request,
        [ErrorToRetry(requests.exceptions.HTTPError, _should_retry_exception)],
    )
    for item in obj['orders']:
        price_value = int(item["current_price"])
        currency = "ETH"
        price_str = f"{Web3.from_wei(price_value, 'ether')} {currency}"
        listing = NFTListing(
            chain=chain,
            address=address,
            token_id=token_id,
            price_str=price_str,
            price_value=price_value,
            order_hash=item["order_hash"],
            protocol_address=item["protocol_address"],
            expiration_time=item["expiration_time"]
        )
        ret.append(listing)
    return ret


def fetch_all_listings(address: str, max_results: Optional[int] = None) -> List[NFTListing]:
    """Fetch all listings for a collection."""
    # NOTE: a given token ID might have more than one listing
    contract = fetch_contract(address)
    slug = contract.slug
    next_cursor = None
    ret = []
    # Arbitary limit to optimize for latency, based on hueristics related to observed number of NFTs listed for blue-chip collections.
    max_results = 300 if max_results is None else max_results
    max_queries = 3
    queries = 0
    limit = min(PAGE_LIMIT, max_results)
    while len(ret) < max_results and queries < max_queries:
        queries += 1
        q = urlencode(dict(
            limit=limit,
            **(dict(next=next_cursor) if next_cursor else {})
        ))
        url = f"{API_V2_URL}/listings/collection/{slug}/all?{q}"

        def _exec_request():
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            return response.json()

        obj = retry_on_exceptions_with_backoff(
            _exec_request,
            [ErrorToRetry(requests.exceptions.HTTPError, _should_retry_exception)],
        )
        for item in obj['listings']:
            offer = item["protocol_data"]["parameters"]["offer"][0]
            item_address = offer["token"]
            if item_address != address:
                continue
            current_price = item["price"]["current"]
            currency = current_price["currency"]
            price_value = int(current_price['value'])
            if currency == "eth":
                price_str = f"{Web3.from_wei(price_value, 'ether')} {currency}"
            else:
                price_str = f"{price_value / 10 ** current_price['decimals']} {currency}"
            listing = NFTListing(
                chain=item["chain"],
                address=item_address,
                token_id=offer["identifierOrCriteria"],
                price_str=price_str,
                price_value=price_value
            )
            ret.append(listing)
        next_cursor = obj.get("next")
        if not next_cursor:
            break
    return ret[:max_results]


def fetch_asset_listing_prices_with_retries(address: str, token_id: str) -> Optional[Dict[str, Union[str, int]]]:
    listings = fetch_listings(address, token_id)
    for listing in listings:
        return dict(price_str=listing.price_str, price_value=listing.price_value)
    return None

def fetch_asset_listing_with_retries(address: str, token_id: str) -> Optional[NFTListing]:
    listings = fetch_listings(address, token_id)
    return listings[0] if len(listings) > 0 else None

def fetch_contract_listing_prices_with_retries(address: str, max_results: Optional[int] = None) -> Dict[str, Dict[str, Union[str, int]]]:
    listings = fetch_all_listings(address, max_results=max_results)
    ret = {}
    for listing in listings:
        if listing.token_id not in ret or ret[listing.token_id].price_value > listing.price_value:
            ret[listing.token_id] = listing
    return {token_id: dict(price_str=listing.price_str, price_value=listing.price_value) for token_id, listing in ret.items()}

def fetch_fulfillment_data_with_retries(network: str, order_hash: str, fulfiller_address: str, protocol_address: str) -> NFTFulfillmentData:
    normalized_network = NETWORKS_MAP.get(network, network)
    url = f"{API_V2_URL}/listings/fulfillment_data"
    data = {
        "listing": {
            "hash": order_hash,
            "chain": normalized_network,
            "protocol_address": protocol_address,
        },
        "fulfiller": {
            "address": fulfiller_address,
        },
    }

    def _exec_request():
        response = requests.post(url, headers=HEADERS, json=data)
        response.raise_for_status()
        return response.json()

    fulfillment_data = retry_on_exceptions_with_backoff(
        _exec_request,
        [ErrorToRetry(requests.exceptions.HTTPError, _should_retry_exception)],
    )
    return NFTFulfillmentData(
        parameters=fulfillment_data["fulfillment_data"]["orders"][0]["parameters"],
        signature=fulfillment_data["fulfillment_data"]["orders"][0]["signature"],
        value_amount=fulfillment_data["fulfillment_data"]["transaction"]["value"],
    )


def _should_retry_exception(exception):
    if exception.response.status_code in (400, 401, 402, 403, 404, 405, 406):
        # forbidden, unauthorized, invalid requests
        return False
    return True
