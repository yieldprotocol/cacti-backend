from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional, Union

from urllib.parse import urlencode
import requests

import env
import utils

from utils import ETH_MAINNET_CHAIN_ID, nft
import utils.timing as timing
from chat.container import ContainerMixin, dataclass_to_container_params

from . import opensea


HEADERS = {
    "accept": "application/json",
    "X-API-Key": utils.CENTER_API_KEY,
}
NETWORKS = [
    "ethereum-mainnet",
    #"polygon-mainnet",
]

API_URL = "https://api.center.dev/v1"
API_V2_URL = "https://api.center.dev/v2"

MAX_RESULTS = 12
PAGE_LIMIT = 12


@dataclass
class NFTCollection(ContainerMixin):
    network: str
    address: str
    name: str
    num_assets: int
    preview_image_url: str

    def container_name(self) -> str:
        return 'display-nft-collection-container'

    def container_params(self) -> Dict:
        return dataclass_to_container_params(self)


@dataclass
class NFTCollectionTraitValue(ContainerMixin):
    trait: str
    value: str
    count: int
    total: int

    def container_name(self) -> str:
        return 'display-nft-collection-trait-value-container'

    def container_params(self) -> Dict:
        return dataclass_to_container_params(self)


@dataclass
class NFTCollectionTrait(ContainerMixin):
    trait: str
    values: List[NFTCollectionTraitValue]

    def container_name(self) -> str:
        return 'display-nft-collection-trait-container'

    def container_params(self) -> Dict:
        return dict(
            trait=self.trait,
            values=[value.struct() for value in self.values],
        )


@dataclass
class NFTCollectionTraits(ContainerMixin):
    collection: NFTCollection
    traits: List[NFTCollectionTrait]

    def container_name(self) -> str:
        return 'display-nft-collection-traits-container'

    def container_params(self) -> Dict:
        return dict(
            network=self.collection.network,
            address=self.collection.address,
            name=self.collection.name,
            traits=[trait.trait for trait in self.traits],
        )


@dataclass
class NFTCollectionTraitValues(ContainerMixin):
    collection: NFTCollection
    trait: NFTCollectionTrait

    def container_name(self) -> str:
        return 'display-nft-collection-trait-values-container'

    def container_params(self) -> Dict:
        return dict(
            network=self.collection.network,
            address=self.collection.address,
            name=self.collection.name,
            trait=self.trait.trait,
            values=[value.value for value in self.trait.values],
        )


@dataclass
class NFTAsset(ContainerMixin):
    network: str
    address: str
    token_id: str
    collection_name: str
    name: str
    preview_image_url: str
    price: Optional[str] = None

    def container_name(self) -> str:
        return 'display-nft-asset-container'

    def container_params(self) -> Dict:
        return dataclass_to_container_params(self)


@dataclass
class NFTAssetTraitValue(ContainerMixin):
    trait: str
    value: str

    def container_name(self) -> str:
        return 'display-nft-asset-trait-value-container'

    def container_params(self) -> Dict:
        return dataclass_to_container_params(self)


@dataclass
class NFTAssetTraits(ContainerMixin):
    asset: NFTAsset
    values: List[NFTAssetTraitValue]

    def container_name(self) -> str:
        return 'display-nft-asset-traits-container'

    def container_params(self) -> Dict:
        return dict(
            asset=self.asset.struct(),
            values=[value.struct() for value in self.values],
        )


@dataclass
class NFTCollectionAssets(ContainerMixin):
    collection: NFTCollection
    assets: List[NFTAsset]

    def container_name(self) -> str:
        return 'display-nft-collection-assets-container'

    def container_params(self) -> Dict:
        return dict(
            collection=self.collection.struct(),
            assets=[asset.struct() for asset in self.assets],
        )
        return dataclass_to_container_params(self)

@dataclass
class NFTAssetList(ContainerMixin):
    assets: List[NFTAsset]

    def container_name(self) -> str:
        return 'display-nft-asset-list-container'

    def container_params(self) -> Dict:
        return dict(
            assets=[asset.struct() for asset in self.assets],
        )

def fetch_nft_search(search_str: str) -> Generator[Union[NFTCollection, NFTAsset], None, None]:
    q = urlencode(dict(
        query=search_str,
        type='collection',  # too noisy otherwise
    ))
    count = 0
    for network in NETWORKS:
        url = f"{API_URL}/{network}/search?{q}"
        timing.log('search_begin')
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        timing.log('search_done')
        obj = response.json()
        for r in obj['results']:
            if not r.get('previewImageUrl'):
                continue
            count += 1
            network = r['id'].split('/')[0]
            if r['type'].lower() == 'collection':
                result = fetch_nft_collection(network, r['address'])
                if not _is_valid_collection(result):
                    continue
            else:
                result = fetch_nft_asset(network, r['address'], r['tokenId'])
            yield result
            timing.log('first_result_done')
    timing.log('%d_results_done' % count)


def _is_valid_collection(collection: NFTCollection) -> bool:
    """Check if this NFT collection is a valid search result."""
    # there should be traits
    collection_traits = fetch_nft_collection_traits(collection.network, collection.address)
    if not collection_traits.traits:
        return False
    # should have listed and valid assets
    assets_for_sale = list(fetch_nft_collection_assets_for_sale(collection.network, collection.address, _skip_timing=True))
    if not assets_for_sale:
        return False
    return True


def _is_valid_asset(asset: NFTAsset) -> bool:
    """Check if this NFT asset is a valid search result."""
    # there should be traits
    # TODO: disabled for now, could be too slow to run this for every asset
    #asset_traits = fetch_nft_asset_traits(asset.network, asset.address, asset.token_id)
    #if not asset_traits.values:
    #    return False

    # as a proxy, filter out assets with no preview image
    if not asset.preview_image_url:
        return False
    return True


def fetch_nft_search_collection_by_trait(network: str, address: str, trait_name: str, trait_value: str, for_sale_only: bool = False) -> Generator[NFTAsset, None, None]:
    timing.log('search_begin')
    if network == "ethereum-mainnet":
        token_prices = opensea.fetch_contract_listing_prices_with_retries(address)
    else:
        token_prices = None

    payload = {"query": {trait_name: [trait_value]}}
    headers = {
        "content-type": "application/json",
        **HEADERS
    }
    limit = PAGE_LIMIT
    offset = 0
    count = 0
    while count < MAX_RESULTS:
        q = urlencode(dict(
            limit=limit,
            offset=offset,
        ))
        url = f"{API_URL}/{network}/{address}/assets/searchByTraits?{q}"
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        timing.log('search_done')
        obj = response.json()
        for item in obj['items']:
            token_id = item['tokenId']
            if token_prices is not None:
                if for_sale_only and token_id not in token_prices:
                    # filter to only for-sale assets
                    continue
                price = token_prices.get(token_id, 'unlisted')
            else:
                price = None
            asset = NFTAsset(
                network=network,
                address=address,
                token_id=token_id,
                collection_name=item['collectionName'],
                name=item['name'],
                preview_image_url=item['mediumPreviewImageUrl'],
                price=price,
            )
            yield asset
            timing.log('first_result_done')
            count += 1
            if count >= MAX_RESULTS:
                break
        if obj['onLastPage']:
            break
        offset += limit
    timing.log('%d_results_done' % count)


def fetch_nft_collection(network: str, address: str) -> NFTCollection:
    url = f"{API_URL}/{network}/{address}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    obj = response.json()
    return NFTCollection(
        network=network,
        address=address,
        name=obj['name'],
        num_assets=obj['numAssets'],
        preview_image_url=obj['smallPreviewImageUrl'],
    )


def fetch_nft_collection_assets(network: str, address: str) -> NFTCollectionAssets:
    collection = fetch_nft_collection(network, address)
    token_ids = [str(i + 1) for i in range(collection.num_assets)]
    if collection.network == "ethereum-mainnet":
        token_prices = opensea.fetch_contract_listing_prices_with_retries(address)
    else:
        token_prices = None

    limit = min(PAGE_LIMIT, len(token_ids))
    offset = 0
    assets = []
    while len(assets) < MAX_RESULTS and offset < len(token_ids):
        payload = {"assets": [
            {"Address": address, "TokenID": token_id}
            for token_id in token_ids[offset: offset + limit]
        ]}
        url = f"{API_URL}/{network}/assets"
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        obj = response.json()
        for item in obj:
            if not item:
                continue
            token_id = item['tokenId']
            if token_prices is not None:
                price = token_prices.get(token_id, 'unlisted')
            else:
                price = None
            asset = NFTAsset(
                network=network,
                address=address,
                token_id=token_id,
                collection_name=item['collectionName'],
                name=item['name'],
                preview_image_url=item['mediumPreviewImageUrl'],
                price=price,
            )
            if not _is_valid_asset(asset):
                continue
            assets.append(asset)
        offset += limit
    assets = assets[:MAX_RESULTS]
    return NFTCollectionAssets(
        collection=collection,
        assets=assets,
    )


def fetch_nft_collection_assets_for_sale(network: str, address: str, _skip_timing: bool = False) -> Generator[NFTAsset, None, None]:
    # we set _skip_timing=True if we are using this as an internal helper, to avoid cluttering
    # logs with irrelevant events
    if not _skip_timing:
        timing.log('search_begin')
    collection = fetch_nft_collection(network, address)
    if collection.network == "ethereum-mainnet":
        token_prices = opensea.fetch_contract_listing_prices_with_retries(address)
        token_ids = list(token_prices.keys())
        token_ids.sort(key=lambda token_id: int(token_id))
    else:
        #assert 0, f'unsupported network: {collection.network}'
        # for now, we fall back to showing some results
        token_prices = None
        token_ids = [str(i + 1) for i in range(collection.num_assets)]

    limit = min(PAGE_LIMIT, len(token_ids))
    offset = 0
    count = 0
    while count < MAX_RESULTS and offset < len(token_ids):
        payload = {"assets": [
            {"Address": address, "TokenID": token_id}
            for token_id in token_ids[offset: offset + limit]
        ]}
        url = f"{API_URL}/{network}/assets"
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        if not _skip_timing:
            timing.log('search_done')
        obj = response.json()
        for item in obj:
            if not item:
                continue
            token_id = item['tokenId']
            if token_prices is not None:
                price = token_prices.get(token_id, 'unlisted')
            else:
                price = None
            asset = NFTAsset(
                network=network,
                address=address,
                token_id=token_id,
                collection_name=item['collectionName'],
                name=item['name'],
                preview_image_url=item['mediumPreviewImageUrl'],
                price=price,
            )
            if not _is_valid_asset(asset):
                continue
            yield asset
            if not _skip_timing:
                timing.log('first_result_done')
            count += 1
            if count >= MAX_RESULTS:
                break
        offset += limit
    if not _skip_timing:
        timing.log('%d_results_done' % count)


def fetch_nft_collection_traits(network: str, address: str) -> NFTCollectionTraits:
    collection = fetch_nft_collection(network, address)
    limit = PAGE_LIMIT
    offset = 0
    traits = []
    while len(traits) < MAX_RESULTS:
        q = urlencode(dict(
            limit=limit,
            offset=offset,
        ))
        url = f"{API_URL}/{network}/{address}/traits?{q}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        obj = response.json()
        for item in obj['items']:
            total = 0
            for v in item['values']:
                total += v['count']
            trait = NFTCollectionTrait(
                trait=item['trait'],
                values=[
                    NFTCollectionTraitValue(
                        trait=item['trait'],
                        value=v['value'],
                        count=v['count'],
                        total=total,
                    ) for v in item['values']
                ],
            )
            traits.append(trait)
        if obj['onLastPage']:
            break
        offset += limit
    return NFTCollectionTraits(
        collection=collection,
        traits=traits,
    )


def fetch_nft_collection_trait_values(network: str, address: str, trait: str) -> NFTCollectionTraitValues:
    collection = fetch_nft_collection(network, address)
    limit = PAGE_LIMIT
    offset = 0
    values = []
    while len(values) < MAX_RESULTS:
        q = urlencode(dict(
            limit=limit,
            offset=offset,
        ))
        url = f"{API_URL}/{network}/{address}/traits/{trait}?{q}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        obj = response.json()
        total = 0
        for item in obj['items']:
            total += item['count']
        for item in obj['items']:
            value = NFTCollectionTraitValue(
                trait=trait,
                value=item['value'],
                count=item['count'],
                total=total,
            )
            values.append(value)
        if obj['onLastPage']:
            break
        offset += limit
    return NFTCollectionTraitValues(
        collection=collection,
        trait=NFTCollectionTrait(
            trait=trait,
            values=values,
        ),
    )


def fetch_nft_asset(network: str, address: str, token_id: str) -> NFTAsset:
    url = f"{API_URL}/{network}/{address}/{token_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    obj = response.json()
    return NFTAsset(
        network=network,
        address=address,
        token_id=token_id,
        collection_name=obj['collectionName'],
        name=obj['name'],
        preview_image_url=obj['mediumPreviewImageUrl'],
    )


def fetch_nft_asset_traits(network: str, address: str, token_id: str) -> NFTAssetTraits:
    if network == "ethereum-mainnet":
        token_price = opensea.fetch_asset_listing_prices_with_retries(address, token_id) or 'unlisted'
    else:
        token_price = None
    url = f"{API_URL}/{network}/{address}/{token_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    obj = response.json()
    asset = NFTAsset(
        network=network,
        address=address,
        token_id=token_id,
        collection_name=obj['collectionName'],
        name=obj['name'],
        preview_image_url=obj['mediumPreviewImageUrl'],
        price=token_price,
    )
    values = []
    for attrib in obj.get('metadata', {}).get('attributes', []):
        value = NFTAssetTraitValue(
            trait=attrib['trait_type'],
            value=attrib['value'],
        )
        values.append(value)
    return NFTAssetTraits(
        asset=asset,
        values=values,
    )

def fetch_nfts_owned_by_address_or_domain(network: str, address_or_domain: str) ->  Generator[NFTAsset, None, None]:
    """Currently only fetches the latest 25 NFTs as per block number."""
    # TODO: Add pagination once we have a UI component such as a Carousel to support it.
    normalized_network = None
    if not network:
        normalized_network = "ethereum-mainnet"
    else:
        if 'ethereum' in network.lower():
            normalized_network = "ethereum-mainnet"
        else:
            return "Network not supported"
    # TODO: What to do if it's a forked network?

    timing.log('fetch_started')

    limit = PAGE_LIMIT
    offset = 0
    sortBy = '-blockNumber'
    assets = []
    q = urlencode(dict(
        sortBy=sortBy,
        limit=limit,
        offset=offset,
    ))
    url = f"{API_V2_URL}/{normalized_network}/{address_or_domain}/nfts-owned?{q}"

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)
        return "Invalid address or domain"
    
    timing.log('fetch_done')

    obj = response.json()
    for item in obj['items']:
        nft_address = item['address']
        nft_token_id = item['tokenID']
        nft_asset = fetch_nft_asset(normalized_network, nft_address, nft_token_id) 
        assets.append(nft_asset)

    # In dev, tester's wallet would only have NFTs on the fork so fallback to fetching from contract on the fork
    # But only fallback if the results from Center are empty to allow for normal display of assets for non-tester addresses.
    if not env.is_prod() and len(assets) == 0:
        dev_results_from_contract = nft.dev_fetch_nfts_from_contract_by_owner(address_or_domain, ETH_MAINNET_CHAIN_ID)
        for r in dev_results_from_contract:
            nft_asset = fetch_nft_asset(normalized_network, r['contract_address'], r['token_id'])
            assets.append(nft_asset)

    timing.log('results_done')

    result = NFTAssetList(assets=assets)
    return result