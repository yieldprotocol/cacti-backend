import os

from web3 import Web3
import tiktoken
from langchain.llms import OpenAI
from ens import ENS

import env


def _get_weaviate_url(config):
    return f"{config.get('protocol', 'https')}://{config['user']}:{config['password']}@{config['host']}:{config['port']}"


def _get_postgres_url(config, database_name):
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{database_name}"


WEAVIATE_URL = _get_weaviate_url(env.env_config['weaviate'])
CHATDB_URL = _get_postgres_url(env.env_config['chatdb'], 'chatdb')
SCRAPEDB_URL = _get_postgres_url(env.env_config['scrapedb'], 'scrapedb')

OPENAI_API_KEY = "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"
CENTER_API_KEY = os.getenv('CENTER_API_KEY', 'key8f1af05afe473107c3ea2556')
ETHERSCAN_API_KEY = 'ZCUTVCPHAJ5YRNB6SZTJN9ZV24FBEX86GJ'
OPENSEA_API_KEY = os.getenv('OPENSEA_API_KEY', '')


def set_api_key():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    OpenAI.api_key = OPENAI_API_KEY


w3 = Web3(Web3.HTTPProvider('https://rpc.tenderly.co/fork/8c2fe457-1702-42f8-a1a3-a5f24b606f36'))
tokenizer = tiktoken.encoding_for_model("text-davinci-003")
ns = ENS.fromWeb3(w3)


def get_token_len(s: str) -> int:
    return len(tokenizer.encode(s))
