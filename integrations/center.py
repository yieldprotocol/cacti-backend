from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from urllib.parse import urlencode
import requests

import utils
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
MAX_RESULTS = 10
PAGE_LIMIT = 100


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


def fetch_nft_search(search_str: str) -> List[Union[NFTCollection, NFTAsset]]:
    q = urlencode(dict(
        query=search_str,
        type='collection',  # too noisy otherwise
    ))
    ret = []
    for network in NETWORKS:
        url = f"{API_URL}/{network}/search?{q}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        obj = response.json()
        for r in obj['results']:
            if not r.get('previewImageUrl'):
                continue
            network = r['id'].split('/')[0]
            if r['type'].lower() == 'collection':
                result = fetch_nft_collection(network, r['address'])
                if not _is_valid_collection(result):
                    continue
            else:
                result = fetch_nft_asset(network, r['address'], r['tokenId'])
            ret.append(result)
    return ret


def _is_valid_collection(collection: NFTCollection) -> bool:
    """Check if this NFT collection is a valid search result."""
    # there should be traits
    collection_traits = fetch_nft_collection_traits(collection.network, collection.address)
    if not collection_traits.traits:
        return False
    # should have listed and valid assets
    collection_assets = fetch_nft_collection_assets(collection.network, collection.address)
    if not collection_assets.assets:
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


def fetch_nft_search_collection_by_trait(network: str, address: str, trait_name: str, trait_value: str) -> List[NFTAsset]:
    if network == "ethereum-mainnet":
        listings = opensea.fetch_contract_listings_with_retries(address)
        token_ids = set([listing.token_id for listing in listings])
    else:
        token_ids = None

    payload = {"query": {trait_name: [trait_value]}}
    headers = {
        "content-type": "application/json",
        **HEADERS
    }
    limit = PAGE_LIMIT
    offset = 0
    ret = []
    while len(ret) < MAX_RESULTS:
        q = urlencode(dict(
            limit=limit,
            offset=offset,
        ))
        url = f"{API_URL}/{network}/{address}/assets/searchByTraits?{q}"
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        obj = response.json()
        for item in obj['items']:
            asset = NFTAsset(
                network=network,
                address=address,
                token_id=item['tokenId'],
                collection_name=item['collectionName'],
                name=item['name'],
                preview_image_url=item['mediumPreviewImageUrl'],
            )
            if token_ids is not None and asset.token_id not in token_ids:
                continue
            ret.append(asset)
        if obj['onLastPage']:
            break
        offset += limit
    return ret


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
    if collection.network == "ethereum-mainnet":
        listings = opensea.fetch_contract_listings_with_retries(collection.address)
        token_ids = list(sorted(set([listing.token_id for listing in listings]), key=lambda token_id: int(token_id)))
    else:
        token_ids = [str(i + 1) for i in range(collection.num_assets)]

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
            asset = NFTAsset(
                network=network,
                address=address,
                token_id=item['tokenId'],
                collection_name=item['collectionName'],
                name=item['name'],
                preview_image_url=item['mediumPreviewImageUrl'],
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
