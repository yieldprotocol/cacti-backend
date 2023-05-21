import os

from web3 import Web3
import tiktoken
from langchain.llms import OpenAI
from ens import ENS
import functools
import traceback
import context
import env

from .constants import OPENAI_API_KEY, TENDERLY_FORK_URL

def _get_weaviate_url(config):
    return f"{config.get('protocol', 'https')}://{config['user']}:{config['password']}@{config['host']}:{config['port']}"


def _get_postgres_url(config, database_name):
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{database_name}"


WEAVIATE_URL = _get_weaviate_url(env.env_config['weaviate'])
CHATDB_URL = _get_postgres_url(env.env_config['chatdb'], 'chatdb')
SCRAPEDB_URL = _get_postgres_url(env.env_config['scrapedb'], 'scrapedb')


def set_api_key():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    OpenAI.api_key = OPENAI_API_KEY


w3 = Web3(Web3.HTTPProvider(TENDERLY_FORK_URL))
tokenizer = tiktoken.encoding_for_model("text-davinci-003")
ns = ENS.from_web3(w3)


def estimate_gas(tx):
        return hex(context.get_web3_provider().eth.estimate_gas(tx))

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