from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from urllib.parse import urlencode
import requests
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


def fetch_nft_buy(network: str, address: str, token_id: str) -> str:
    network = NETWORKS_MAP.get(network, network)
    # TODO: for now, we just omit network altogether since frontend only works with ethereum
    return f"<|display-buy-nft({address},{token_id})|>"


# this represents an NFT collection
@dataclass
class NFTContract:
    chain: str
    address: str
    slug: str
    name: str
    image_url: str


# this is a listing of an NFT asset
@dataclass
class NFTListing:
    chain: str
    address: str
    token_id: str
    price_str: str
    price_value: int


def fetch_contract(address: str) -> NFTContract:
    """Fetch data about a contract (collection)."""
    url = f"{API_V1_URL}/asset_contract/{address}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    obj = response.json()
    collection = obj["collection"]
    return NFTContract(
        chain=obj["chain_identifier"],
        address=address,
        slug=collection["slug"],
        name=collection["name"],
        image_url=collection["image_url"],
    )


def fetch_listings(address: str, token_id: str) -> List[NFTListing]:
    """Fetch cheapest listing for an asset."""
    chain = "ethereum"
    limit = 1
    next_cursor = None
    ret = []
    while len(ret) < MAX_RESULTS:
        q = urlencode(dict(
            limit=limit,
            asset_contract_address=address,
            token_ids=token_id,
            order_by='eth_price',
            order_direction='asc',
            **(dict(next=next_cursor) if next_cursor else {})
        ))
        url = f"{API_V2_URL}/orders/{chain}/seaport/listings?{q}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        obj = response.json()
        for item in obj['orders']:
            offer = item["protocol_data"]["parameters"]["offer"][0]
            price_value = int(item["current_price"])
            currency = "eth"
            price_str = f"{utils.w3.from_wei(price_value, 'ether')} {currency}"
            listing = NFTListing(
                chain=chain,
                address=address,
                token_id=token_id,
                price_str=price_str,
                price_value=price_value,
            )
            ret.append(listing)
        next_cursor = obj.get("next")
        if not next_cursor:
            break
    return ret


def fetch_all_listings(slug: str) -> List[NFTListing]:
    """Fetch all listings for a collection."""
    # NOTE: a given token ID might have more than one listing
    limit = PAGE_LIMIT
    next_cursor = None
    ret = []
    while len(ret) < MAX_RESULTS:
        q = urlencode(dict(
            limit=limit,
            **(dict(next=next_cursor) if next_cursor else {})
        ))
        url = f"{API_V2_URL}/listings/collection/{slug}/all?{q}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        obj = response.json()
        for item in obj['listings']:
            offer = item["protocol_data"]["parameters"]["offer"][0]
            current_price = item["price"]["current"]
            currency = current_price["currency"]
            price_value = int(current_price['value'])
            if currency == "eth":
                price_str = f"{utils.w3.from_wei(price_value, 'ether')} {currency}"
            else:
                price_str = f"{price_value / 10 ** current_price['decimals']} {currency}"
            listing = NFTListing(
                chain=item["chain"],
                address=offer["token"],
                token_id=offer["identifierOrCriteria"],
                price_str=price_str,
                price_value=price_value,
            )
            ret.append(listing)
        next_cursor = obj.get("next")
        if not next_cursor:
            break
    return ret


def fetch_asset_listing_prices_with_retries(address: str, token_id: str) -> Optional[str]:

    def _get_listing_prices():
        listings = fetch_listings(address, token_id)
        for listing in listings:
            return listing.price_str
        return None

    return retry_on_exceptions_with_backoff(
        _get_listing_prices,
        [ErrorToRetry(requests.exceptions.HTTPError)],
    )


def fetch_contract_listing_prices_with_retries(address: str) -> Dict[str, str]:

    def _get_listing_prices():
        contract = fetch_contract(address)
        listings = fetch_all_listings(contract.slug)
        ret = {}
        for listing in listings:
            if listing.token_id not in ret or ret[listing.token_id].price_value > listing.price_value:
                ret[listing.token_id] = listing
        return {token_id: listing.price_str for token_id, listing in ret.items()}

    return retry_on_exceptions_with_backoff(
        _get_listing_prices,
        [ErrorToRetry(requests.exceptions.HTTPError)],
    )
