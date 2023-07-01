import inspect
import os
import json
import yaml

from web3 import Web3
import tiktoken
from langchain.llms import OpenAI
from ens import ENS
import functools
import traceback
import context

from .constants import OPENAI_API_KEY, TENDERLY_FORK_URL


def yaml2functions(file_path):
    functions = []
    with open(file_path, 'r') as file:
        dict_yml = yaml.safe_load(file)
    for _, value in dict_yml.items():
        dict_ = {}
        dict_['name'] = value['name']
        dict_['description'] = value['description']
        dict_['parameters'] = value['parameters']
        functions.append(dict_)
    return functions


def yaml2widgetsdoc(file_path):
    doc = ""
    with open(file_path, 'r') as file:
        dict_yaml = yaml.safe_load(file)
    for _, values in dict_yaml.items():
        doc += f"Widget magic command: {values['widget_command']}\n"
        doc += f"Description of widget: {values['description']}\n"
        doc += f"Required parameters:\n"
        for param_name, prop in values['parameters']['properties'].items():
            doc += "-{" + param_name + "}" + f": {prop['description']}\n"
        if len(values["return_value_description"].strip()) > 0: 
            doc += f"Return value description:\n-{values['return_value_description']}\n"
        doc += "---\n"
    return doc.strip().strip('---').strip()

yaml_file_path = f"{os.getcwd()}/knowledge_base/widgets.yaml"
WIDGETS = yaml2widgetsdoc(yaml_file_path)
FUNCTIONS = yaml2functions(yaml_file_path)


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
