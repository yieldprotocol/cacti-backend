from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from urllib.parse import urlencode
import requests

import utils
from chat.container import ContainerMixin


# For now just search one network
HEADERS = {
    "accept": "application/json",
    "X-API-Key": utils.CENTER_API_KEY,
}
NETWORKS = [
    "ethereum-mainnet",
    "polygon-mainnet",
]
API_URL = "https://api.center.dev/v1"


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
        return dict(
            network=self.network,
            address=self.address,
            name=self.name,
            numAssets=self.num_assets,
            previewImageUrl=self.preview_image_url,
        )


@dataclass
class NFTCollectionTraitValue:
    count: int
    value: str

    def __str__(self) -> str:
        return f'{self.value} (x{self.count})'


@dataclass
class NFTCollectionTrait:
    trait: str
    total_values: int
    values: List[NFTCollectionTraitValue]

    def __str__(self) -> str:
        return f'An NFT collection trait "{self.trait}" with {self.total_values} values: {", ".join(map(str, self.values))}.'


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
        return dict(
            network=self.network,
            address=self.address,
            tokenId=self.token_id,
            collectionName=self.collection_name,
            name=self.name,
            previewImageUrl=self.preview_image_url,
        )


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
            network = r['id'].split('/')[0]
            if r['type'].lower() == 'collection':
                result = fetch_nft_collection(network, r['address'])
            else:
                result = fetch_nft_asset(network, r['address'], r['tokenId'])
            ret.append(result)
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


def fetch_nft_collection_traits(network: str, address: str) -> List[NFTCollectionTrait]:
    limit = 100
    offset = 0
    ret = []
    while True:
        q = urlencode(dict(
            limit=limit,
            offset=offset,
        ))
        url = f"{API_URL}/{network}/{address}/traits?{q}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        obj = response.json()
        for item in obj['items']:
            trait = NFTCollectionTrait(
                trait=item['trait'],
                values=[NFTCollectionTraitValue(value=v['value'], count=v['count']) for v in item['values']],
                total_values=item['totalValues'],
            )
            ret.append(trait)
        if obj['onLastPage']:
            break
        offset += limit
    return ret


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
