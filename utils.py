import os

from web3 import Web3
import tiktoken
from langchain.llms import OpenAI
from ens import ENS
import functools
import traceback
import context
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

TENDERLY_FORK_URL = "https://rpc.tenderly.co/fork/902db63e-9c5e-415b-b883-5701c77b3aa7"


def set_api_key():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    OpenAI.api_key = OPENAI_API_KEY


w3 = Web3(Web3.HTTPProvider(TENDERLY_FORK_URL))
tokenizer = tiktoken.encoding_for_model("text-davinci-003")
ns = ENS.from_web3(w3)


def get_token_len(s: str) -> int:
    return len(tokenizer.encode(s))


# Error handling
class ConnectedWalletRequired(Exception):
    pass


class FetchError(Exception):
    pass


class ExecError(Exception):
    pass

def error_wrap(fn):
    @functools.wraps(fn)
    def wrapped_fn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ConnectedWalletRequired:
            return "A connected wallet is required. Please connect one and try again."
        except FetchError as e:
            return str(e)
        except ExecError as e:
            return str(e)
        except Exception as e:
            traceback.print_exc()
            return f'Got exception evaluating {fn.__name__}(args={args}, kwargs={kwargs}): {e}'
    return wrapped_fn


def ensure_wallet_connected(fn):
    @functools.wraps(fn)
    def wrapped_fn(*args, **kwargs):
        if not context.get_wallet_address():
            raise ConnectedWalletRequired()
        return fn(*args, **kwargs)
    return wrapped_fn