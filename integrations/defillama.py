import requests
from dataclasses import dataclass

DEFILLAMA_API_URL = "https://yields.llama.fi"


@dataclass
class Yield:
    token: str
    chain: str
    project: str
    apy: float

    def __str__(self) -> str:
        return f"Token: {self.token}, Chain: {self.chain}, Project: {self.project}, APY: {self.apy}%"


def fetch_yields(token, chain, count) -> str:
    # Convert the inferred canonical chain name to what DefiLlama uses for result filtering
    if chain.lower() == "binance":
        chain = "BSC"
    elif chain.lower() == "mainnet":
        chain = "Ethereum"

    # If no inferred count, default to 5
    if count == "*":
        count = 5

    url = f"{DEFILLAMA_API_URL}/pools"
    response = requests.get(url)
    response.raise_for_status()
    obj = response.json()
    yields = obj["data"]
    filtered_yields = list(filter(lambda yield_obj: _filter_yield_list(token, chain, yield_obj), yields))
    filtered_yields.sort(key=lambda yield_obj: yield_obj["apy"], reverse=True)
    selected_yields = filtered_yields[:int(count)]

    answer = "Here are the Yields:"
    for y in selected_yields:
        data_obj = Yield(y["symbol"], y["chain"], y["project"], y["apy"])
        answer += "\n{}".format(data_obj)

    return answer


def _filter_yield_list(input_token, input_chain, yield_obj) -> bool:
    normalized_symbol = yield_obj["symbol"].lower()
    normalized_chain = yield_obj["chain"].lower()
    input_token = input_token.lower()
    input_chain = input_chain.lower()

    if input_token == "*" and input_chain == "*":
        return True

    if input_chain == "*":
        return normalized_symbol == input_token

    if input_token == "*":
        return normalized_chain == input_chain

    return normalized_symbol == input_token and normalized_chain == input_chain
