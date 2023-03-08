import functools
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import traceback

import requests
from urllib.parse import urlencode
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.prompts.base import BaseOutputParser
from web3 import Web3

import context
import utils
import registry
import streaming
from integrations import etherscan, defillama
from .index_lookup import IndexLookupTool


RE_COMMAND = re.compile(r"\<\|(?P<command>[^(]+)\((?P<params>[^)<{}]*)\)\|\>")


TEMPLATE = '''You are a web3 widget tool. You have access to a list of widget magic commands that you can delegate work to, by invoking them and chaining them together, to provide a response to an input query. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>". They can only be used with all parameters having known and assigned values, otherwise, they have to be kept secret. The command may either have a display- or a fetch- prefix. When you return a display- command, the user will see data, an interaction box, or other inline item rendered in its place. When you return a fetch- command, data is fetched over an API and injected in place. Fetch- commands can be nested in other magic commands, and will be resolved recursively, for example, "<|command1(parameter1, <|command2(parameter2)|>)|>". Simple expressions can be resolved with the "<|fetch-eval(expression)|>" command, for example, the ratio of 2 numbers can be calculated as "<|fetch-eval(number1/number2)|>". Users cannot type or use magic commands, so do not tell them to use them. Fill in the command with parameters as inferred from the input. If there are missing parameters, do not use magic commands but mention what parameters are needed instead. If the widget requires a connected wallet that is not available, state that a connected wallet is needed, and don't use any magic commands. If there is no appropriate widget available, explain that more information is needed. Do not make up a non-existent widget magic command, only use the applicable ones for the situation, and only if all parameters are available. You might need to use the output of widget magic commands as the input to another to get your final answer. Here are the widgets that may be relevant:
---
{task_info}
---
Use the following format:

## Thought: describe what you are trying to solve from input
## Widgets: names of relevant widget magic commands to respond to input
## Parameters: input parameter-value pairs representing inputs to the above widget magic command(s), expressed in the correct format as known info strings, or as calls to other fetch- commands
## Response: tool response to input synthesized using only widget magic commands with their respective input parameters replaced with values
## Thought: I have resolved all input parameters to widgets.

Is wallet connected: {connected}
Tool input: {question}
## Thought:'''


@registry.register_class
class IndexWidgetTool(IndexLookupTool):
    """Tool for searching a widget index and figuring out how to respond to the question."""

    _chain: LLMChain

    def __init__(
            self,
            *args,
            **kwargs
    ) -> None:
        prompt = PromptTemplate(
            input_variables=["task_info", "question", "connected"],
            template=TEMPLATE,
        )

        new_token_handler = kwargs.get('new_token_handler')
        response_buffer = ""
        response_state = 0  # finite-state machine state
        response_prefix = "## Response:"

        def injection_handler(token):
            nonlocal new_token_handler, response_buffer, response_state, response_prefix

            response_buffer += token
            if response_state == 0:  # we are still waiting for response_prefix to appear
                if response_prefix not in response_buffer:
                    # keep waiting
                    return
                else:
                    # we have found the response_prefix, trim everything before that
                    response_state = 1
                    response_buffer = response_buffer[response_buffer.index(response_prefix) + len(response_prefix):]

            if response_state == 1:  # we are going to output the response incrementally, evaluating any fetch commands
                while '<|' in response_buffer:
                    if '|>' in response_buffer:
                        # parse fetch command
                        response_buffer = iterative_evaluate(response_buffer)
                        if response_buffer == response_buffer:  # nothing resolved
                            if len(response_buffer.split('<|')) == len(response_buffer.split('|>')):
                                # matching pairs of open/close, just flush
                                break
                            else:
                                # keep waiting
                                return
                    else:
                        # keep waiting
                        return
                token = response_buffer
                response_buffer = ""
                new_token_handler(token)
                if '\n' in token:
                    # we have found a line-break in the response, switch to the terminal state to mask subsequent output
                    response_state = 2

        chain = streaming.get_streaming_chain(prompt, injection_handler)
        super().__init__(
            *args,
            _chain=chain,
            content_description="widget magic command definitions for users to invoke web3 transactions or live data when the specific user action or transaction is clear. You can look up live prices, DeFi yields, wallet balances, ENS information, token contract addresses, do transfers or swaps, or search for NFTs and retrieve data about NFTs. It cannot help the user with understanding how to use the app or how to perform certain actions.",
            input_description="a standalone query phrase with all relevant contextual details mentioned explicitly without using pronouns in order to invoke the right widget",
            output_description="a summarized answer with relevant magic command for widget(s), or a question prompt for more information to be provided",
            **kwargs
        )

    def _run(self, query: str) -> str:
        """Query index and answer question using document chunks."""
        task_info = super()._run(query)
        example = {
            "task_info": task_info,
            "question": query,
            "connected": "Yes" if context.get_wallet_address() else "No",
            "stop": "User",
        }
        result = self._chain.run(example)
        return result.strip()


def iterative_evaluate(phrase: str) -> str:
    while True:
        eval_phrase = RE_COMMAND.sub(replace_match, phrase)
        if eval_phrase == phrase:
            break
        phrase = eval_phrase
    return phrase


def sanitize_str(s: str) -> str:
    s = s.strip()
    if s.startswith('"') and s.endswith('"') or s.startswith("'") and s.endswith("'"):
        s = s[1:-1]
    return s


def replace_match(m: re.Match) -> str:
    command = m.group('command')
    params = m.group('params')
    params = list(map(sanitize_str, params.split(','))) if params else []
    print('found command:', command, params)
    if command == 'fetch-nft-search':
        return str(fetch_nft_search(*params))
    elif command == 'fetch-nft-collection':
        return str(fetch_nft_collection(*params))
    elif command == 'fetch-nft-collection-traits':
        return str(fetch_nft_collection_traits(*params))
    elif command == 'fetch-nft-asset':
        return str(fetch_nft_asset(*params))
    elif command == 'fetch-eval':
        return str(safe_eval(*params))
    elif command == 'fetch-wallet':
        return str(context.get_wallet_address())
    elif command == 'fetch-balance':
        return str(fetch_balance(*params))
    elif command == 'fetch-eth-in':
        return str(fetch_eth_in(*params))
    elif command == 'fetch-eth-out':
        return str(fetch_eth_out(*params))
    elif command == 'fetch-gas':
        return str(fetch_gas(*params))
    elif command == 'fetch-yields':
        return str(fetch_yields(*params))
    elif command == 'ens-from-address':
        return str(ens_from_address(*params))
    elif command == 'address-from-ens':
        return str(address_from_ens(*params))
    elif command.startswith('display-'):
        return m.group(0)
    else:
        # unrecognized command, just return for now
        # assert 0, 'unrecognized command: %s' % m.group(0)
        return m.group(0)


def error_wrap(fn):
    @functools.wraps(fn)
    def wrapped_fn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            return f'Got exception evaluating {fn.__name__}(args={args}, kwargs={kwargs}): {e}'
    return wrapped_fn


@error_wrap
def safe_eval(params: str) -> str:
    # TODO: make this more powerful
    for op in ['+', '-', '*', '/']:
        if op in params:
            params1, params2 = params.split(op, 1)
            return str(eval(f"{float(params1)} {op} {float(params2)}"))
    return params


@error_wrap
def fetch_balance(token: str, wallet_address: str) -> str:
    contract_address = etherscan.get_contract_address(token)
    return etherscan.get_balance(contract_address, wallet_address)


@error_wrap
def fetch_eth_in(wallet_address: str) -> str:
    return etherscan.get_all_eth_to_address(wallet_address)


@error_wrap
def fetch_eth_out(wallet_address: str) -> str:
    return etherscan.get_all_eth_from_address(wallet_address)


@error_wrap
def fetch_gas(wallet_address: str) -> str:
    return etherscan.get_all_gas_for_address(wallet_address)


# For now just search one network
HEADERS = {
    "accept": "application/json",
    "X-API-Key": utils.CENTER_API_KEY,
}
NETWORKS = [
    "ethereum-mainnet",
    "polygon-mainnet",
]
API_URL = f"https://api.center.dev/v1"


class DescriptiveList(list):
    def __str__(self) -> str:
        return "\n".join([
            f"Here is a list of {len(self)} items:",
        ] + [str(item) for item in self])


@dataclass
class NFTCollection:
    network: str
    address: str
    name: str
    num_assets: int

    def __str__(self) -> str:
        return f'An NFT collection on network "{self.network}" with address "{self.address}" and name "{self.name}" having {self.num_assets} assets.'


@dataclass
class NFTCollectionTraitValue:
    count: int
    value: str

    def __str__(self) -> str:
        return f'{self.value} (x{self.count})'


@dataclass
class NFTCollectionTrait:
    trait: str
    total_values: int
    values: List[NFTCollectionTraitValue]

    def __str__(self) -> str:
        return f'An NFT collection trait "{self.trait}" with {self.total_values} values: {", ".join(map(str, self.values))}.'


@dataclass
class NFTAsset:
    network: str
    address: str
    token_id: str
    collection_name: str
    name: str

    def __str__(self) -> str:
        return f'An NFT asset on network "{self.network}" with address "{self.address}" and id "{self.token_id}" and name "{self.name}" from collection "{self.collection_name}".'


@error_wrap
def fetch_nft_search(search_str: str) -> List[Union[NFTCollection, NFTAsset]]:
    q = urlencode(dict(
        query=search_str,
        type='collection',  # too noisy otherwise
    ))
    ret = []
    for network in NETWORKS:
        url = f"{API_URL}/{network}/search?{q}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        obj = response.json()
        for r in obj['results']:
            network = r['id'].split('/')[0]
            if r['type'].lower() == 'collection':
                result = nftcollection(network, r['address'])
            else:
                result = nftasset(network, r['address'], r['tokenId'])
            ret.append(result)
    return DescriptiveList(ret)


@error_wrap
def fetch_nft_collection(network: str, address: str) -> NFTCollection:
    url = f"{API_URL}/{network}/{address}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    obj = response.json()
    return NFTCollection(
        network=network,
        address=address,
        name=obj['name'],
        num_assets=obj['numAssets'],
    )


@error_wrap
def fetch_nft_collection_traits(network: str, address: str) -> NFTCollection:
    limit = 100
    offset = 0
    ret = []
    while True:
        q = urlencode(dict(
            limit=limit,
            offset=offset,
        ))
        url = f"{API_URL}/{network}/{address}/traits?{q}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        obj = response.json()
        for item in obj['items']:
            trait = NFTCollectionTrait(
                trait=item['trait'],
                values=[NFTCollectionTraitValue(value=v['value'], count=v['count']) for v in item['values']],
                total_values=item['totalValues'],
            )
            ret.append(trait)
        if obj['onLastPage']:
            break
        offset += limit
    return DescriptiveList(ret)


@error_wrap
def fetch_nft_asset(network: str, address: str, token_id: str) -> NFTAsset:
    url = f"{API_URL}/{network}/{address}/{token_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    obj = response.json()
    return NFTAsset(
        network=network,
        address=address,
        token_id=token_id,
        collection_name=obj['collection_name'],
        name=obj['name'],
    )


@error_wrap
def fetch_yields(token, chain, count) -> str:
    return defillama.fetch_yields(token, chain, count)


def ens_from_address(address) -> str:
    try:
        domain = utils.ns.name(address)
        if domain is None:
            return f"No ENS domain for {address}"
        else:
            return f"The ENS domain for {address} is {domain}"
    except ValueError as valueError:
        return f"Invalid address {address}"
    except Exception as e:
        traceback.print_exc()
        return f"Unable to process address {address}"


def address_from_ens(domain) -> str:
    try:
        address = utils.ns.address(domain)
        if address is None:
            return f"No address for {domain}"
        else:
            return f"The address for {domain} is {address}"
    except Exception as e:
        traceback.print_exc()
        return f"Unable to process domain {domain}"
