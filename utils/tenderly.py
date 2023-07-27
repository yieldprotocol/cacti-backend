import requests

from utils import TENDERLY_API_KEY, TENDERLY_PROJECT_API_BASE_URL

TENDERLY_PROJECT_URL = f"{TENDERLY_PROJECT_API_BASE_URL}/fork"

def create_fork():
    if not TENDERLY_API_KEY:
        raise Exception("TENDERLY_API_KEY required to run simulations in isolated forks")

    print("Creating fork...")

    payload = {
        "network_id": "1",
        "block_number": 17297193 # https://etherscan.io/block/17297193
    }
    res = requests.post(TENDERLY_PROJECT_URL, json=payload, headers={"X-Access-Key": TENDERLY_API_KEY})
    res.raise_for_status()
    return res.json()['root_transaction']['fork_id']

def remove_fork(fork_id: str):
    res = requests.delete(f"{TENDERLY_PROJECT_URL}/{fork_id}", headers={"X-Access-Key": TENDERLY_API_KEY})
    res.raise_for_status()
    print(f"Fork deleted: {fork_id}")