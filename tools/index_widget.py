import functools
import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict
import traceback

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.prompts.base import BaseOutputParser

import context
import utils
from utils import error_wrap, check_wallet_connected, ConnectedWalletRequired, FetchError, ExecError
import registry
import streaming
from chat.container import ContainerMixin, dataclass_to_container_params
from integrations import (
    etherscan, defillama, center, opensea,
)
from ui_workflows import (
    aave, ens
)
from .index_lookup import IndexLookupTool

from ui_workflows.multistep_handler import register_ens_domain

RE_COMMAND = re.compile(r"\<\|(?P<command>[^(]+)\((?P<params>[^)<{}]*)\)\|\>")


TEMPLATE = '''You are a web3 widget tool. You have access to a list of widget magic commands that you can delegate work to, by invoking them and chaining them together, to provide a response to an input query. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>" specifying the command and its input parameters. They can only be used with all parameters having known and assigned values, otherwise, they have to be kept secret. The command may either have a display- or a fetch- prefix. When you return a display- command, the user will see data, an interaction box, or other inline item rendered in its place. When you return a fetch- command, data is fetched over an API and injected in place. Users cannot type or use magic commands, so do not tell them to use them. Fill in the command with parameters as inferred from the input. If there are missing parameters, do not use magic commands but mention what parameters are needed instead. If there is no appropriate widget available, explain that more information is needed. Do not make up a non-existent widget magic command, only use the applicable ones for the situation, and only if all parameters are available. You might need to use the output of widget magic commands as the input to another to get your final answer. Here are the widgets that may be relevant:
---
{task_info}
---
Use the following format:

## Widget Command: most relevant widget magic command to respond to input
## Known Parameters: input parameter-value pairs representing inputs to the above widget magic command
## Response: return the widget magic command with ALL its respective input parameter values (omit parameter names)

Tool input: {question}
## Widget Command:'''


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
            input_variables=["task_info", "question"],
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
                                # NB: for better frontend parsing of nested widgets, we need an invariant that
                                # there are no two independent widgets on the same line, otherwise we can't
                                # detect the closing tag properly when there is nesting.
                                response_buffer = response_buffer.replace('|>', '|>\n')
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
            content_description="widget magic command definitions for users to invoke web3 transactions or live data when the specific user action or transaction is clear. You can look up live prices, DeFi yields, wallet balances, ENS information, token contract addresses, do transfers or swaps or deposit tokens to farm yields, or search for NFTs, and retrieve data about NFT collections, assets, trait names and trait values. It cannot help the user with understanding how to use the app or how to perform certain actions.",
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
    elif command == 'fetch-nft-collection-assets-by-trait':
        return str(fetch_nft_search_collection_by_trait(*params, for_sale_only=False))
    elif command == 'fetch-nft-collection-assets-for-sale-by-trait':
        return str(fetch_nft_search_collection_by_trait(*params, for_sale_only=True))
    elif command == 'fetch-nft-collection-info':
        # return str(fetch_nft_collection(*params))
        # we also fetch some collection assets as a convenience
        return str(fetch_nft_collection_assets(*params))
    elif command == 'fetch-nft-collection-assets-for-sale':
        return str(fetch_nft_collection_assets_for_sale(*params))
    elif command == 'fetch-nft-collection-traits':
        return str(fetch_nft_collection_traits(*params))
    elif command == 'fetch-nft-collection-trait-values':
        return str(fetch_nft_collection_trait_values(*params))
    # elif command == 'fetch-nft-asset-info':
    #    return str(fetch_nft_asset(*params))
    elif command == 'fetch-nft-asset-traits':
        return str(fetch_nft_asset_traits(*params))
    elif command == 'fetch-nft-buy-asset':
        return str(fetch_nft_buy(*params))
    elif command == 'fetch-balance':
        return str(fetch_balance(*params))
    elif command == 'fetch-my-balance':
        return str(fetch_my_balance(*params))
    elif command == 'fetch-eth-in':
        return str(fetch_eth_in(*params))
    elif command == 'fetch-eth-out':
        return str(fetch_eth_out(*params))
    elif command == 'fetch-gas':
        return str(fetch_gas(*params))
    elif command == 'fetch-yields':
        return str(fetch_yields(*params))
    elif command == 'exec-project-deposit':
        return str(exec_project_operation(*params, operation='Supply'))
    elif command == 'exec-project-borrow':
        return str(exec_project_operation(*params, operation='Borrow'))
    elif command == 'exec-project-repay':
        return str(exec_project_operation(*params, operation='Repay'))
    elif command == 'exec-project-withdraw':
        return str(exec_project_operation(*params, operation='Withdraw'))
    elif command == 'ens-from-address':
        return str(ens_from_address(*params))
    elif command == 'address-from-ens':
        return str(address_from_ens(*params))
    elif command == 'register-ens-domain':
        return str(register_ens_domain(*params))
    elif command == 'set-ens-text':
        return str(set_ens_text(*params))
    elif command.startswith('display-'):
        return m.group(0)
    else:
        # unrecognized command, just return for now
        # assert 0, 'unrecognized command: %s' % m.group(0)
        return m.group(0)

@error_wrap
def fetch_balance(token: str, wallet_address: str) -> str:
    if not wallet_address or wallet_address == 'None':
        raise FetchError(f"Please specify the wallet address to check the token balance of.")
    contract_address = etherscan.get_contract_address(token)
    if not contract_address:
        raise FetchError(f"Could not look up contract address of {token}. Please try a different one.")
    return etherscan.get_balance(contract_address, wallet_address)


@error_wrap
def fetch_my_balance(token: str) -> str:
    wallet_address = context.get_wallet_address()
    if not wallet_address:
        raise ConnectedWalletRequired
    return fetch_balance(token, wallet_address)


@error_wrap
def fetch_eth_in(wallet_address: str) -> str:
    return etherscan.get_all_eth_to_address(wallet_address)


@error_wrap
def fetch_eth_out(wallet_address: str) -> str:
    return etherscan.get_all_eth_from_address(wallet_address)


@error_wrap
def fetch_gas(wallet_address: str) -> str:
    return etherscan.get_all_gas_for_address(wallet_address)


class ListContainer(ContainerMixin, list):
    def message_prefix(self) -> str:
        num = len(self)
        if num > 0:
            return f"I found {num} result{'s' if num > 1 else ''}: "
        else:
            return "I did not find any results."

    def container_name(self) -> str:
        return 'display-list-container'

    def container_params(self) -> Dict:
        return dict(
            items=[item.struct() for item in self],
        )


@dataclass
class TableHeader:
    field_name: str
    display_name: str

    def container_params(self) -> Dict:
        return dataclass_to_container_params(self)


@dataclass
class TableContainer(ContainerMixin):
    headers: List[TableHeader]
    rows: List[ContainerMixin]
    message_prefix_str: str = ""

    def message_prefix(self) -> str:
        return self.message_prefix_str

    def container_name(self) -> str:
        return 'display-table-container'

    def container_params(self) -> Dict:
        return dict(
            headers=[header.container_params() for header in self.headers],
            rows=[row.struct() for row in self.rows],
        )


@error_wrap
def fetch_nft_search(search_str: str) -> str:
    ret = center.fetch_nft_search(search_str)
    return str(ListContainer(ret))


@error_wrap
def fetch_nft_search_collection_by_trait(
        network: str, address: str, trait_name: str, trait_value: str, for_sale_only: bool = False) -> str:
    ret = center.fetch_nft_search_collection_by_trait(
        network, address, trait_name, trait_value, for_sale_only=for_sale_only)
    return str(ListContainer(ret))


@error_wrap
def fetch_nft_collection(network: str, address: str) -> str:
    return str(center.fetch_nft_collection(network, address))


@error_wrap
def fetch_nft_collection_assets(network: str, address: str) -> str:
    ret = center.fetch_nft_collection_assets(network, address)
    return str(ret)


@error_wrap
def fetch_nft_collection_assets_for_sale(network: str, address: str) -> str:
    ret = center.fetch_nft_collection_assets_for_sale(network, address)
    return str(ListContainer(ret))


@error_wrap
def fetch_nft_collection_traits(network: str, address: str) -> str:
    ret = center.fetch_nft_collection_traits(network, address)
    return str(ret)


@error_wrap
def fetch_nft_collection_trait_values(network: str, address: str, trait: str) -> str:
    ret = center.fetch_nft_collection_trait_values(network, address, trait)
    return str(ret)


@error_wrap
def fetch_nft_asset(network: str, address: str, token_id: str) -> str:
    return str(center.fetch_nft_asset(network, address, token_id))


@error_wrap
def fetch_nft_asset_traits(network: str, address: str, token_id: str) -> str:
    return str(center.fetch_nft_asset_traits(network, address, token_id))


@error_wrap
def fetch_nft_buy(network: str, address: str, token_id: str) -> str:
    ret = opensea.fetch_nft_buy(network, address, token_id)
    return ret


@error_wrap
def fetch_yields(token, network, count) -> str:
    yields = defillama.fetch_yields(token, network, count)

    headers = [
        TableHeader(field_name="project", display_name="Project"),
        TableHeader(field_name="tvlUsd", display_name="TVL"),
        TableHeader(field_name="apy", display_name="APY"),
        TableHeader(field_name="apyAvg30d", display_name="30 day Avg. APY")
    ]

    if network == '*':
        headers = [TableHeader(field_name="network", display_name="Network")] + headers

    if token == '*':
        headers = [TableHeader(field_name="token", display_name="Token")] + headers

    table_container = TableContainer(headers=headers, rows=yields)
    return str(table_container)


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


@dataclass
class TxPayloadForSending(ContainerMixin):
    user_request_status: Literal['success', 'error']
    parsed_user_request: str = ''
    tx: Optional[dict] = None  # from, to, value, data, gas
    is_approval_tx: bool = False
    error_msg: Optional[str] = None
    description: str = ''

    def container_name(self) -> str:
        return 'display-tx-payload-for-sending-container'

    def container_params(self) -> Dict:
        return dataclass_to_container_params(self)

@error_wrap
def exec_project_operation(project: str, token: str, amount: str, operation: str = '') -> TxPayloadForSending:
    if project.lower() == 'aave':
        return exec_aave_operation(token, amount, operation)
    else:
        return "Project not supported."


def exec_aave_operation(token: str, amount: str, operation: str = '') -> TxPayloadForSending:
    if not operation:
        raise ExecError("Operation needs to be specified.")
    wallet_chain_id = 1
    wallet_address = context.get_wallet_address()
    if not wallet_address:
        raise ConnectedWalletRequired
    wf = aave.AaveUIWorkflow(wallet_chain_id, wallet_address, token, operation, float(amount))
    result = wf.run()
    return TxPayloadForSending(
        user_request_status=result.status,
        parsed_user_request=result.parsed_user_request,
        tx=result.tx,
        is_approval_tx=result.is_approval_tx,
        error_msg=result.error_msg,
        description=result.description
    )

@error_wrap
@check_wallet_connected
def set_ens_text(domain: str, key: str, value: str) ->TxPayloadForSending:
    wallet_chain_id = 1 # TODO: get from context
    wallet_address = context.get_wallet_address()
    user_chat_message_id = context.get_user_chat_message_id() or user_chat_message_id

    params = {
        'domain': domain,
        'key': key,
        'value': value,
    }

    wf = ens.ENSSetTextWorkflow(wallet_chain_id, wallet_address, 'set-ens-text', params)
    result = wf.run()

    return TxPayloadForSending(
        user_request_status=result.status,
        tx=result.tx,
        error_msg=result.error_msg,
        description=result.description
    )