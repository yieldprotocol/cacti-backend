import requests

DEFILLAMA_API_URL = "https://yields.llama.fi"


def fetch_yields():
    url = f"{DEFILLAMA_API_URL}/pools"
    response = requests.get(url)
    response.raise_for_status()
    obj = response.json()
    return obj["data"]
