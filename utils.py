import os

from web3 import Web3
import tiktoken
from langchain.llms import OpenAI


OPENAI_API_KEY = "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"
WEAVIATE_URL = "https://chatweb3:q0jficzXOA69T5FWgAeT@chatweb3.func.ai:5050"
CHATDB_URL = "postgresql://chatdb:lVIu2U0lBctiYBScboAJ@chatweb3.func.ai:5433/chatdb"
SCRAPEDB_URL = "postgresql://chatdb:lVIu2U0lBctiYBScboAJ@chatweb3.func.ai:5433/scrapedb"
CENTER_API_KEY = 'key8f1af05afe473107c3ea2556'  # TODO: replace with yield version
ETHERSCAN_API_KEY = 'ZCUTVCPHAJ5YRNB6SZTJN9ZV24FBEX86GJ'


def set_api_key():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    OpenAI.api_key = OPENAI_API_KEY


w3 = Web3(Web3.HTTPProvider('https://rpc.tenderly.co/fork/8c2fe457-1702-42f8-a1a3-a5f24b606f36'))
tokenizer = tiktoken.encoding_for_model("text-davinci-003")


def get_token_len(s: str) -> int:
    return len(tokenizer.encode(s))
