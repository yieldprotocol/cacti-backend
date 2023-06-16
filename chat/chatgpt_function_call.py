# This chat variant determines if the user's query is related to a widget or a search
import re
import time
import json
import uuid
import traceback
from dataclasses import dataclass, asdict
from typing import Any, Dict, Generator, List, Optional, Union, Literal, TypedDict, Callable

from gpt_index.utils import ErrorToRetry, retry_on_exceptions_with_backoff
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    SystemMessage
)

import context
import utils
import utils.timing as timing
from utils.common import FUNCTIONS
import registry
import streaming
from .base import (
    BaseChat, Response, ChatHistory2
)
from ui_workflows import (
    aave, ens
)
from ui_workflows.multistep_handler import register_ens_domain, exec_aave_operation
from tools.index_widget import *


@registry.register_class
class ChatGPTFunctionCallChat(BaseChat):
    def __init__(self, model_name: Optional[str] = "gpt-3.5-turbo-0613") -> None:
        super().__init__()
        self.model_name = model_name

    def receive_input(
            self,
            history: ChatHistory2,
            userinput: str,
            send: Callable,
            message_id: Optional[uuid.UUID] = None,
            before_message_id: Optional[uuid.UUID] = None,
    ) -> None:
        userinput = userinput.strip()
        history.messages += [HumanMessage(content=userinput, additional_kwargs={'message_id':message_id, 'before_message_id': before_message_id})]

        timing.init()

        bot_chat_message_id = None
        bot_response = ''
        has_sent_bot_response = False

        def bot_flush(response):
            nonlocal bot_chat_message_id
            response = response.strip()
            send(Response(
                response=response,
                still_thinking=False,
                actor='bot',
                operation='replace',
            ), last_chat_message_id=bot_chat_message_id, before_message_id=before_message_id)
            history.messages.append(AIMessage(content=response, additional_kwargs={'message_id':bot_chat_message_id, 'before_message_id':before_message_id}))

        def bot_new_token_handler(token):
            nonlocal bot_chat_message_id, bot_response, has_sent_bot_response

            bot_response += token
            if not bot_response.strip():
                # don't start returning something until we have the first non-whitespace char
                return

            timing.log('first_visible_bot_token')
            bot_chat_message_id = send(Response(
                response=token,
                still_thinking=False,
                actor='bot',
                operation='append' if bot_chat_message_id is not None else 'create',
            ), last_chat_message_id=bot_chat_message_id, before_message_id=before_message_id)
            has_sent_bot_response = True

        model = streaming.get_streaming_llm(bot_new_token_handler, model_name=self.model_name)

        ai_message = model.predict_messages(history.messages, functions=FUNCTIONS)
        with context.with_request_context(history.wallet_address, message_id):
            if not has_sent_bot_response:  # when the output has function_call  
                bot_response = evaluate(ai_message)
                bot_flush(bot_response)
        timing.log('response_done')

        response = f'Timings - {timing.report()}'
        system_chat_message_id = send(Response(response=response, actor='system'), before_message_id=before_message_id)
        history.messages.append(SystemMessage(content=response, additional_kwargs={'message_id':system_chat_message_id, 'before_message_id':before_message_id}))

def evaluate(message: BaseMessage):
    command = message.additional_kwargs['function_call']['name']
    params = list(json.loads(message.additional_kwargs['function_call']['arguments']).values())

    print('found command:', command, params)
    if command == 'fetch_nft_search':
        return fetch_nft_search(*params)
    elif command == 'fetch_price':
        return str(fetch_price(*params))
    elif command == 'fetch_nft_collection_assets_by_trait':
        return fetch_nft_search_collection_by_trait(*params, for_sale_only=False)
    elif command == 'fetch_nft_collection_assets_for_sale_by_trait':
        return fetch_nft_search_collection_by_trait(*params, for_sale_only=True)
    elif command == 'fetch_nft_collection_info':
        # return str(fetch_nft_collection(*params))
        # we also fetch some collection assets as a convenience
        return str(fetch_nft_collection_assets(*params))
    elif command == 'fetch_nft_collection_assets_for_sale':
        return fetch_nft_collection_assets_for_sale(*params)
    elif command == 'fetch_nft_collection_traits':
        return str(fetch_nft_collection_traits(*params))
    elif command == 'fetch_nft_collection_trait_values':
        return str(fetch_nft_collection_trait_values(*params))
    # elif command == 'fetch_nft_asset_info':
    #    return str(fetch_nft_asset(*params))
    elif command == 'fetch_nft_asset_traits':
        return str(fetch_nft_asset_traits(*params))
    elif command == 'fetch_nft_buy_asset':
        return str(fetch_nft_buy(*params))
    elif command == 'fetch_balance':
        return str(fetch_balance(*params))
    elif command == 'fetch_my_balance':
        return str(fetch_my_balance(*params))
    elif command == 'fetch_eth_in':
        return str(fetch_eth_in(*params))
    elif command == 'fetch_eth_out':
        return str(fetch_eth_out(*params))
    elif command == 'fetch_gas':
        return str(fetch_gas(*params))
    elif command == 'fetch_yields':
        return str(fetch_yields(*params))
    elif command == 'fetch_app_info':
        return fetch_app_info(*params)
    elif command == 'fetch_scraped_sites':
        return fetch_scraped_sites(*params)
    elif command == aave.AaveSupplyContractWorkflow.WORKFLOW_TYPE:
        return str(exec_aave_operation(*params, operation='supply'))
    elif command == aave.AaveBorrowContractWorkflow.WORKFLOW_TYPE:
        return str(exec_aave_operation(*params, operation='borrow'))
    elif command == aave.AaveRepayContractWorkflow.WORKFLOW_TYPE:
        return str(exec_aave_operation(*params, operation='repay'))
    elif command == aave.AaveWithdrawContractWorkflow.WORKFLOW_TYPE:
        return str(exec_aave_operation(*params, operation='withdraw'))
    elif command == 'ens_from_address':
        return str(ens_from_address(*params))
    elif command == 'address_from_ens':
        return str(address_from_ens(*params))
    elif command == ens.ENSRegistrationContractWorkflow.WORKFLOW_TYPE:
        return str(register_ens_domain(*params))
    elif command == ens.ENSSetTextWorkflow.WORKFLOW_TYPE:
        return str(set_ens_text(*params))
    elif command == ens.ENSSetPrimaryNameWorkflow.WORKFLOW_TYPE:
        return str(set_ens_primary_name(*params))
    elif command == ens.ENSSetAvatarNFTWorkflow.WORKFLOW_TYPE:
        return str(set_ens_avatar_nft(*params))
    elif command.startswith('display_'):
        return f"<|{'-'.join(command.split('_'))}({','.join(params)})|>"
    else:
        # unrecognized command, just return for now
        # assert 0, 'unrecognized command: %s' % f"<|{'-'.join(command.split('_'))}({','.join(params)})|>"
        return f"<|{'-'.join(command.split('_'))}({','.join(params)})|>"

