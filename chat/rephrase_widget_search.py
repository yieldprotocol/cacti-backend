# This chat variant determines if the user's query is related to a widget or a search
import re
import time
import uuid
import traceback
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable


from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

import context
import utils
from utils import error_wrap, ensure_wallet_connected, ConnectedWalletRequired, FetchError, ExecError
import registry
import streaming
from chat.container import ContainerMixin, dataclass_to_container_params
from .base import (
    BaseChat, ChatHistory, Response, ChatOutputParser,
)
from integrations import (
    etherscan, defillama, center, opensea,
)
from ui_workflows import (
    aave, ens
)
from ui_workflows.multistep_handler import register_ens_domain, exec_aave_operation


RE_COMMAND = re.compile(r"\<\|(?P<command>[^(]+)\((?P<params>[^)<{}]*)\)\|\>")

# TODO: make this few-shot on real examples instead of dummy ones
# REPHRASE_TEMPLATE = '''
# Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question. You should assume that the question is related to web3.

# ## Example:

# Chat History:
# User: Who created Ethereum?
# Assistant: Vitalik Buterin
# Follow Up Input: What about AAVE?
# Standalone question: Who created AAVE?

# ## Example:

# Chat History:
# User: Who created Ethereum?
# Assistant: Vitalik Buterin
# User: What about AAVE?
# Assistant: Stani Kulechov
# Follow Up Input: When was that?
# Standalone question: When were Ethereum and AAVE created?

# ## Example:

# Chat History:
# User: Who created Ethereum?
# Assistant: Vitalik Buterin
# Follow Up Input: What is AAVE?
# Standalone question: What is AAVE?

# ## Example:

# Chat History:
# User: Who created Ethereum?
# Assistant: Vitalik Buterin
# User: What is AAVE?
# Assistant: AAVE is a decentralized finance protocol that allows users to borrow and lend digital assets. It is a protocol built on Ethereum and is powered by a native token, Aave.
# Follow Up Input: Bitoin?
# Standalone question: What is Bitcoin?

# ## Example:

# Chat History:
# {history}
# Follow Up Input: {question}
# Standalone question:'''

REPHRASE_TEMPLATE = \
'''You are a rephrasing agent. You will be given a query which you have to rephrase, explicitly restating the task without pronouns and restating details based on the conversation history and new input. Restate verbatim ALL details/names/figures/facts/etc from past observations relevant to the task and ALL related entities.
# Chat History:
# {history}
# Input: {question}
# Rephrased Input:'''

# TEMPLATE = '''You are a web3 widget tool. You have access to a list of widget magic commands that you can delegate work to, by invoking them and chaining them together, to provide a response to an input query. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>" specifying the command and its input parameters. They can only be used with all parameters having known and assigned values, otherwise, they have to be kept secret. The command may either have a display- or a fetch- prefix. When you return a display- command, the user will see data, an interaction box, or other inline item rendered in its place. When you return a fetch- command, data is fetched over an API and injected in place. Users cannot type or use magic commands, so do not tell them to use them. Fill in the command with parameters as inferred from the input. If there are missing parameters, do not use magic commands but mention what parameters are needed instead. If there is no appropriate widget available, explain that more information is needed. Do not make up a non-existent widget magic command, only use the applicable ones for the situation, and only if all parameters are available. You might need to use the output of widget magic commands as the input to another to get your final answer. Here are the widgets that may be relevant:
# ---
# {task_info}
# ---
# Use the following format:

# ## Widget Command: most relevant widget magic command to respond to input
# ## Known Parameters: input parameter-value pairs representing inputs to the above widget magic command
# ## Response: return the widget magic command with ALL its respective input parameter values (omit parameter names)

# Tool input: {question}
# ## Widget Command:'''

TEMPLATE = '''You are a web3 widget tool. You have access to a list of widget magic commands that you can delegate work to, by invoking them and chaining them together, to provide a response to an input query. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>" specifying the command and its input parameters. They can only be used with all parameters having known and assigned values, otherwise, they have to be kept secret. The command may either have a display- or a fetch- prefix. When you return a display- command, the user will see data, an interaction box, or other inline item rendered in its place. When you return a fetch- command, data is fetched over an API and injected in place. Users cannot type or use magic commands, so do not tell them to use them. Fill in the command with parameters as inferred from the input. If there are missing parameters, do not use magic commands but mention what parameters are needed instead. If there is no appropriate widget available, explain that more information is needed. Do not make up a non-existent widget magic command, only use the applicable ones for the situation, and only if all parameters are available. You might need to use the output of widget magic commands as the input to another to get your final answer. Here are the widgets that may be relevant:
---
{task_info}
---
Use the following format:

## Tool Input: given an input rephrase it, explicitly restating the task without pronouns and restating details based on the conversation history and new input. Restate verbatim ALL details/names/figures/facts/etc from past observations relevant to the task and ALL related entities.
## Widget Command: most relevant widget magic command to respond to input
## Known Parameters: input parameter-value pairs representing inputs to the above widget magic command
## Response: return the widget magic command with ALL its respective input parameter values (omit parameter names)

Input: {question}
## Tool input:'''

@registry.register_class
class RephraseWidgetSearchChat(BaseChat):
    def __init__(self, widget_index: Any, top_k: int = 3, show_thinking: bool = True) -> None:
        super().__init__()
        self.output_parser = ChatOutputParser()
        self.rephrase_prompt = PromptTemplate(
            input_variables=["history", "question"],
            template=REPHRASE_TEMPLATE,
        )
        llm = OpenAI(temperature=0.0,)
        self.rephrase_chain = LLMChain(llm=llm, prompt=self.rephrase_prompt)
        self.widget_prompt = PromptTemplate(
            input_variables=["task_info", "question"],
            template=TEMPLATE,
            output_parser=self.output_parser,
        )
        self.widget_index = widget_index
        self.top_k = top_k
        self.show_thinking = show_thinking

    def receive_input(
            self,
            history: ChatHistory,
            userinput: str,
            send: Callable,
            message_id: Optional[uuid.UUID] = None,
            before_message_id: Optional[uuid.UUID] = None,
    ) -> None:
        userinput = userinput.strip()
        history_string = history.to_string()
        # start = time.time()

        # if history:
        #     # First rephrase the question
        #     question = self.rephrase_chain.run({
        #         "history": history_string.strip(),
        #         "question": userinput,
        #         "stop": "User",
        #     }).strip()
        #     rephrased = True
        # else:
        #     question = userinput
        #     rephrased = False
        # if self.show_thinking and rephrased and userinput != question:
        #     send(Response(response="I think you're asking: " + question, still_thinking=True))
        #     duration = time.time() - start
        #     send(Response(
        #         response=f'Rephrasing took {duration: .2f}s',
        #         actor='system',
        #         still_thinking=True,  # turn on thinking again
        #     ))

        system_chat_message_id = None
        system_response = ''
        bot_chat_message_id = None
        bot_response = ''
        has_sent_bot_response = False

        def system_flush(response):
            nonlocal system_chat_message_id, has_sent_bot_response
            response = response.strip()
            send(Response(
                response=response,
                still_thinking=not has_sent_bot_response,
                actor='system',
                operation='replace',
            ), last_chat_message_id=system_chat_message_id, before_message_id=before_message_id)
            history.add_system_message(response, message_id=system_chat_message_id, before_message_id=before_message_id)

        def bot_flush(response):
            nonlocal bot_chat_message_id
            response = response.strip()
            send(Response(
                response=response,
                still_thinking=False,
                actor='bot',
                operation='replace',
            ), last_chat_message_id=bot_chat_message_id, before_message_id=before_message_id)
            history.add_bot_message(response, message_id=bot_chat_message_id, before_message_id=before_message_id)

        def bot_new_token_handler(token):
            nonlocal bot_chat_message_id, bot_response, system_chat_message_id, system_response, has_sent_bot_response

            if system_chat_message_id is not None:
                system_flush(system_response)
                system_chat_message_id = None
                system_response = ''

            bot_response += token
            if not bot_response.strip():
                # don't start returning something until we have the first non-whitespace char
                return
            bot_chat_message_id = send(Response(
                response=token,
                still_thinking=False,
                actor='bot',
                operation='append' if bot_chat_message_id is not None else 'create',
            ), last_chat_message_id=bot_chat_message_id, before_message_id=before_message_id)
            has_sent_bot_response = True

        new_token_handler = bot_new_token_handler
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

        widgets = self.widget_index.similarity_search(userinput, k=self.top_k)
        task_info = '\n'.join([f'Widget: {widget.page_content}' for widget in widgets])
        example = {
            "task_info": task_info,
            "question": userinput,
            "stop": ["Input", "User"],
        }        
        chain = streaming.get_streaming_chain(self.widget_prompt, injection_handler)

        start = time.time()
        result = chain.run(example).strip()
        duration = time.time() - start

        history.add_interaction(userinput, result)
        if system_chat_message_id is not None:
            send(Response(response = f'system_chat_message_id = {system_chat_message_id}'), before_message_id=before_message_id)
            system_flush(system_response)

        # if bot_chat_message_id is not None:
        #     send(Response(response = f'bot_chat_message_id = {bot_chat_message_id}'), before_message_id=before_message_id)
        #     bot_flush(result)
        # else:
        #     if 'DONE' not in result:
        #         send(Response(response=result), before_message_id=before_message_id)

        response = f'Response generation took {duration: .2f}s'
        system_chat_message_id = send(Response(response=response, actor='system'), before_message_id=before_message_id)
        history.add_system_message(response, message_id=system_chat_message_id, before_message_id=before_message_id)


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
    elif command == 'aave-supply':
        return str(exec_aave_operation(*params, operation='supply'))
    elif command == 'aave-borrow':
        return str(exec_aave_operation(*params, operation='borrow'))
    elif command == 'aave-repay':
        return str(exec_aave_operation(*params, operation='repay'))
    elif command == 'aave-withdraw':
        return str(exec_aave_operation(*params, operation='withdraw'))
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
@ensure_wallet_connected
def set_ens_text(domain: str, key: str, value: str) ->TxPayloadForSending:
    wallet_chain_id = 1 # TODO: get from context
    wallet_address = context.get_wallet_address()
    user_chat_message_id = context.get_user_chat_message_id()

    params = {
        'domain': domain,
        'key': key,
        'value': value,
    }

    wf = ens.ENSSetTextWorkflow(wallet_chain_id, wallet_address, user_chat_message_id, 'set-ens-text', params)
    result = wf.run()

    return TxPayloadForSending(
        user_request_status=result.status,
        tx=result.tx,
        error_msg=result.error_msg,
        description=result.description
    )