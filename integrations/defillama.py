import requests
from dataclasses import dataclass
from typing import Dict, List

from chat.container import ContainerMixin, dataclass_to_container_params

DEFILLAMA_API_URL = "https://yields.llama.fi"


@dataclass
class Yield(ContainerMixin):
    token: str
    network: str
    project: str
    apy: float
    apy_avg_30d: float
    tvl_usd: float

    def container_name(self) -> str:
        return 'display-yield-container'

    def container_params(self) -> Dict:
        return dataclass_to_container_params(self)

def fetch_tvl(protocol) -> str:
    url = f"https://api.llama.fi/tvl/{protocol}"
    response = requests.get(url)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        return "No TVL data available for this protocol"
    obj = response.json()
    return obj

def fetch_yields(token, network, count) -> List[Yield]:
    normalized_network_name = _network_name_normalizer(network)

    # If no inferred count, default to 5
    if count == "*":
        count = 5

    url = f"{DEFILLAMA_API_URL}/pools"
    response = requests.get(url)
    response.raise_for_status()
    obj = response.json()
    yields = obj["data"]
    filtered_yields = list(filter(lambda yield_obj: _filter_yield_list(token, normalized_network_name, yield_obj), yields))
    # Sorting on TVL to select the top N blue-chip projects
    filtered_yields.sort(key=lambda yield_obj: yield_obj["tvlUsd"], reverse=True)
    selected_yields = filtered_yields[:int(count)]

    return [
        Yield(
            yield_obj["symbol"],
            yield_obj["chain"],
            yield_obj["project"],
            "{:.2f}%".format(yield_obj["apy"]),
            "{:.2f}%".format(yield_obj["apyMean30d"]),
            "${:,}".format(yield_obj["tvlUsd"]))
        for yield_obj in selected_yields]


def _filter_yield_list(input_token, input_network, yield_obj) -> bool:
    normalized_symbol = yield_obj["symbol"].lower()
    normalized_network = yield_obj["chain"].lower()
    input_token = input_token.lower()
    input_network = input_network.lower()

    # Only select single-sided yield pools
    if yield_obj["exposure"] != "single" or yield_obj["apy"] == 0 or yield_obj["tvlUsd"] == 0:
        return False

    if input_token == "*" and input_network == "*":
        return True

    if input_network == "*":
        return normalized_symbol == input_token

    if input_token == "*":
        return normalized_network == input_network

    return normalized_symbol == input_token and normalized_network == input_network


def _network_name_normalizer(network: str) -> str:
    # Convert the inferred network name to what DefiLlama uses for filtering
    if "binance" in network.lower():
        return "BSC"
    
    if "ethereum" in network.lower():
        return "Ethereum"
    
    return network