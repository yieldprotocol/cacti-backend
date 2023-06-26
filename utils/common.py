import inspect
import os
import json

from web3 import Web3
import tiktoken
from langchain.llms import OpenAI
from ens import ENS
import functools
import traceback
import context

from .constants import OPENAI_API_KEY, OPENAI_ORGANIZATION, TENDERLY_FORK_URL


with open(f"{os.getcwd()}/knowledge_base/functions.json", 'r') as f:
    FUNCTIONS = json.load(f)


def set_api_key():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    os.environ["OPENAI_ORGANIZATION"] = OPENAI_ORGANIZATION
    OpenAI.api_key = OPENAI_API_KEY
    OpenAI.organization = OPENAI_ORGANIZATION


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

    @functools.wraps(fn)
    def wrapped_generator_fn(*args, **kwargs):
        try:
            for item in fn(*args, **kwargs):
                yield item
        except ConnectedWalletRequired:
            yield "A connected wallet is required. Please connect one and try again."
        except FetchError as e:
            yield str(e)
        except ExecError as e:
            yield str(e)
        except Exception as e:
            traceback.print_exc()
            yield f'Got exception evaluating {fn.__name__}(args={args}, kwargs={kwargs}): {e}'

    if inspect.isgeneratorfunction(fn):
        return wrapped_generator_fn
    else:
        return wrapped_fn


def ensure_wallet_connected(fn):
    @functools.wraps(fn)
    def wrapped_fn(*args, **kwargs):
        if not context.get_wallet_address():
            raise ConnectedWalletRequired()
        return fn(*args, **kwargs)
    return wrapped_fn
