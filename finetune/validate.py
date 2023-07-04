"run : `python -m finetune.validate --auto True`"
import re
import argparse
import random
import random
import collections
import copy
import uuid
import pandas as pd
from typing import Any, Dict, Generator, List, Optional, Union, Literal, TypedDict, Callable, Iterable

from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import SystemMessage, HumanMessage

from integrations.center import (
    NFTCollection, NFTAsset, NFTCollectionAssets, NFTAssetTraits, NFTAssetTraitValue,
    NFTCollectionTraits, NFTCollectionTrait, NFTCollectionTraitValue,
)
from chat.base import ChatHistory, ChatMessage
import chat
import config
import utils.timing as timing
from utils.common import WIDGETS
from tools.index_widget import (
    StreamingListContainer,
    _get_result_list_prefix,
    WIDGET_START,
    WIDGET_END,
)
from .generate import (
    Conversation, Message, StreamingListContainer,
    stream_to_str,
    handle_empty_params,
)

# SYSTEM_MESSAGE_AUTOEVAL = """You have to imitate a human tester who asks a chatbot queries related to web3. The tester wants the bot to fail, so his queries are a bit complicated and not clear.
# The queries are based on the given widget command as the bot invokes it in response to the query. 
# Use real tokens, addresses and other widget command's parameters. Try to use tokens which the bot might not have heard of.
# Ask one question at a time. Do not use widget command in the query."""
SYSTEM_MESSAGE_AUTOEVAL = """You have to imitate a human tester who tests a chatbot designed specifically to answer web3 related queries. The bot works by taking in a user query and routing it to one of the many widget commands defined by the bot developer.
To produce a test sample please use the following format and think step by step:
## Task : a task which may utilize one or more of the given widget commands.
## Test Sample : a list of tuples (query, widget_command) which should be used sequentially to complete the task.
To parse your 'Test Sample', it should be in a specific format. Example : [("repay 100 DAI tokens to Aave", "<|aave-repay(DAI,100)|>"), ("withdraw 50 DAI tokens from zksync L2 to mainnet L1", "<|display-zksync-withdraw(DAI,50)|>")]
Use real tokens, addresses and other widget command's parameters. Also, try to use tokens which the bot might not have heard of."""

RE_COMMAND = re.compile(r"\[\(\"(.*)\"\)\]", re.DOTALL)

chat_configs = [
    dict(
        type='chat.fine_tuned.FineTunedChat',
        widget_index=None,
        model_name='curie:ft-yield-inc-2023-05-30-20-19-41',
        evaluate_widgets=False,
    ),
    dict(
        type='chat.fine_tuned.FineTunedChat',
        widget_index=None,
        model_name='curie:ft-yield-inc:gen-500-2023-06-08-08-20-51',
        evaluate_widgets=False,
    ),
    dict(
        type='chat.fine_tuned.FineTunedChat',
        widget_index=None,
        model_name='curie:ft-yield-inc:gen-1k-2023-06-09-18-41-36',
        evaluate_widgets=False,
    ),
    dict(
        type='chat.fine_tuned.FineTunedChat',
        widget_index=None,
        model_name='curie:ft-yield-inc:gen-1000b-2023-06-11-03-18-04',
        evaluate_widgets=False,
    ),
]
chat_configs = [
    dict(
        type='chat.rephrase_widget_search.RephraseWidgetSearchChat',
        widget_index=config.widget_index,
        top_k=18,
        evaluate_widgets=False,
    ),
    dict(
        type='chat.rephrase_widget_search2.RephraseWidgetSearchChat',
        widget_index=config.widget_index,
        top_k=18,
        evaluate_widgets=False,
    ),
    dict(
        type="chat.basic_agent.BasicAgentChat",
        tools=[
            dict(
                type="tools.index_widget.IndexWidgetTool",
                _streaming=True,
                name="WidgetIndexAnswer",
                index=config.widget_index,
                top_k=10,
                evaluate_widgets=False,
            ),
        ],
    ),
]
chat_configs = [
    dict(
        type='chat.chatgpt_function_call.ChatGPTFunctionCallChat',
        model_name='gpt-4-0613',
        widget_index=config.widget_index,
        top_k=32,
        evaluate_widgets=False,
    ),
]

def get_nft_flow() -> Iterable[Message]:
    query = "penguin"
    yield Message("user", f"find some {query} NFTs")

    ETH_NETWORK = "ethereum-mainnet"
    network1 = ETH_NETWORK
    address1 = "0xBd3531dA5CF5857e7CfAA92426877b022e612cf8"
    name1 = "PudgyPenguins"
    network2 = ETH_NETWORK
    address2 = "0x31F3bba9b71cB1D5e96cD62F0bA3958C034b55E9"
    name2 = "Party Penguins"

    collection1 = NFTCollection(
        network=f"{network1}",
        address=f"{address1}",
        name=f"{name1}",
        num_assets=123,
        preview_image_url="http://preview_image_url1",
    )
    collection2 = NFTCollection(
        network=f"{network2}",
        address=f"{address2}",
        name=f"{name2}",
        num_assets=456,
        preview_image_url="https://preview_image_url2",
    )
    yield Message("bot", f"<|fetch-nft-search({query})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="append", item=collection1),
        StreamingListContainer(operation="append", item=collection2),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(2)),
    ]))

    yield Message("user", f"let's look at {name2}")

    token_id1 = "1234"
    token_name1 = "Asset #1234"
    token_id2 = "1235"
    token_name2 = "Asset #1235"
    price = "1.2 ETH"
    assets = [
        NFTAsset(
            network=collection2.network,
            address=collection2.address,
            token_id=token_id1,
            collection_name=collection2.name,
            name=token_name1,
            preview_image_url='',
            price=None,
        ),
        NFTAsset(
            network=collection2.network,
            address=collection2.address,
            token_id=token_id2,
            collection_name=collection2.name,
            name=token_name2,
            preview_image_url='',
            price=price,
        ),
    ]
    collection_assets_container = NFTCollectionAssets(
        collection=collection2,
        assets=assets,
    )
    yield Message("bot", f"<|fetch-nft-collection-info({network2},{address2})|>", str(collection_assets_container))

    yield Message("user", f"what are the assets for sale for this collection")

    yield Message("bot", f"<|fetch-nft-collection-assets-for-sale({network2},{address2})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="append", item=assets[1]),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(1)),
    ]))

    yield Message("user", f"what are the traits for this asset")

    values = [
        NFTAssetTraitValue(
            trait='Hat',
            value='Pirate Hat',
        ),
        NFTAssetTraitValue(
            trait='Head',
            value='Big',
        ),
    ]
    asset_traits_container = NFTAssetTraits(
        asset=assets[1],
        values=values,
    )
    yield Message("bot", f"<|fetch-nft-asset-traits({network2},{address2},{token_id2})|>", str(asset_traits_container))

    yield Message("user", f"what are the traits for this collection")

    collection_traits = [
        NFTCollectionTrait(
            trait='trait1',
            values=[
                NFTCollectionTraitValue(trait='trait1', value='value1', count=10, total=100),
                NFTCollectionTraitValue(trait='trait1', value='value2', count=10, total=100),
            ],
        ),
        NFTCollectionTrait(
            trait='trait2',
            values=[
                NFTCollectionTraitValue(trait='trait2', value='another_value1', count=10, total=100),
                NFTCollectionTraitValue(trait='trait2', value='another_value2', count=10, total=100),
            ],
        ),
    ]
    collection_traits_container = NFTCollectionTraits(
        collection=collection2,
        traits=collection_traits,
    )
    yield Message("bot", f"<|fetch-nft-collection-traits({network2},{address2})|>", str(collection_traits_container))

    trait_name = 'trait1'
    trait_value = 'value1'
    yield Message("user", f"what are the assets with {trait_value} for {trait_name}?")

    yield Message("bot", f"<|fetch-nft-collection-assets-by-trait({network2},{address2},{trait_name},{trait_value})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="append", item=assets[1]),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(1)),
    ]))

    yield Message("user", f"which of these are for sale?")
    yield Message("bot", f"<|fetch-nft-collection-assets-for-sale-by-trait({network2},{address2},{trait_name},{trait_value})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(0)),
    ]))

    trait_value2 = 'value2'
    yield Message("user", f"what about assets with {trait_value2}?")
    yield Message("bot", f"<|fetch-nft-collection-assets-for-sale-by-trait({network2},{address2},{trait_name},{trait_value2})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="append", item=assets[0]),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(1)),
    ]))

    yield Message("user", f"let's buy this one.")
    yield Message("bot", f"<|fetch-nft-buy-asset({network2},{address2},{token_id1})|>", f"<|display-buy-nft({address2},{token_id1})|>")


def get_wallet_balance_flow() -> Iterable[Message]:
    token = "ETH"
    balance = 123.456
    yield Message("user", f"what's my balance of {token}?")
    yield Message("bot", f"<|fetch-my-balance({token})|>", f"{balance}")
    token2 = "USDC"
    balance2 = 654.321
    yield Message("user", f"how about {token2}?")
    yield Message("bot", f"<|fetch-my-balance({token2})|>", f"{balance2}")
    address1 = "0x123456"
    balance3 = 0.123
    yield Message("user", f"what about that in {address1}?")
    yield Message("bot", f"<|fetch-balance({token2},{address1})|>", f"{balance3}")
    address2 = "0x789123"
    balance4 = 0.1531
    yield Message("user", f"and {address2}?")
    yield Message("bot", f"<|fetch-balance({token2},{address2})|>", f"{balance4}")


def get_app_info_flow() -> Iterable[Message]:
    yield Message("user", f"what can I do in this app?")
    query = "What can this app do?"
    response = "Lots of stuff."
    yield Message("bot", f"<|fetch-app-info({query})|>", f"{response}")
    yield Message("user", f"how do I use this app?")
    query = "How do I interact with this app?"
    response = "Chat with it"
    yield Message("bot", f"<|fetch-app-info({query})|>", f"{response}")


def get_scraped_sites_flow() -> Iterable[Message]:
    yield Message("user", f"who invented Ethereum?")
    query = "Who invented Ethereum?"
    response = "Vitalik."
    yield Message("bot", f"<|fetch-scraped-sites({query})|>", f"{response}")
    yield Message("user", f"What is AAVE")
    query = "What is AAVE?"
    response = "A protocol"
    yield Message("bot", f"<|fetch-scraped-sites({query})|>", f"{response}")


def get_transfer_flow() -> Iterable[Message]:
    token = "ETH"
    address = "0x1234"
    amount = "123"
    yield Message("user", f"transfer {token} to {address}")
    yield handle_empty_params(Message("bot", f"<|display-transfer({token},,{address})|>", f"What quantity would you like to transfer?"))
    yield Message("user", f"{amount}")
    yield Message("bot", f"<|display-transfer({token},{amount},{address})|>")
    token = "USDC"
    address = "0x4321"
    amount = "456"
    yield Message("user", f"send {amount} of {token} to {address}")
    yield Message("bot", f"<|display-transfer({token},{amount},{address})|>")


def get_price_flow() -> Iterable[Message]:
    base_token = "ETH"
    quote_token = "USD"
    yield Message("user", f"what's the price of {base_token}?")
    yield Message("bot", f"<|fetch-price({base_token},{quote_token})|>", "1234")
    quote_token = "USDC"
    yield Message("user", f"what's the price of {base_token} in {quote_token}?")
    yield Message("bot", f"<|fetch-price({base_token},{quote_token})|>", "1235")


def get_swap_flow() -> Iterable[Message]:
    sell_token = "ETH"
    buy_token = "USDC"
    keyword = "SELLAMOUNT"
    amount = 123
    yield Message("user", f"swap {sell_token} for {buy_token}")
    yield handle_empty_params(Message("bot", f"<|display-uniswap({sell_token},{buy_token},,)|>", f"What quantity of tokens would you like to swap?"))
    yield Message("user", f"swap {amount} {sell_token} for {buy_token}")
    yield Message("bot", f"<|display-uniswap({sell_token},{buy_token},{keyword},{amount})|>")
    yield Message("user", f"actually swap {sell_token} for {amount} {buy_token}")
    keyword = "BUYAMOUNT"
    yield Message("bot", f"<|display-uniswap({sell_token},{buy_token},{keyword},{amount})|>")


def get_ens_lookup_flow() -> Iterable[Message]:
    address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    domain = "mydomain"
    yield Message("user", f"ens for {address}")
    yield Message("bot", f"<|ens-from-address({address})|>", domain)
    address = "0x1234567890"
    domain = "abcdef.eth"
    yield Message("user", f"address for {domain}")
    yield Message("bot", f"<|address-from-ens({domain})|>", address)


def get_ens_registration_flow() -> Iterable[Message]:
    domain = "abcdef.eth"
    yield Message("user", f"register {domain}")
    yield Message("bot", f"<|register-ens-domain({domain})|>", "A workflow step was presented.")
    yield Message("user", f"set primary ENS name to {domain}")
    yield Message("bot", f"<|set-ens-primary-name({domain})|>", "A transaction was presented for sending.")
    query = "Rumble Kong"
    yield Message("user", f"find some {query} NFTs")

    network = "ethereum-mainnet"
    address1 = "0xEf0182dc0574cd5874494a120750FD222FdB909a"
    address2 = "0x0b87320F22C94e290e763c2F337dC0B44693a548"
    collection1 = NFTCollection(
        network=network,
        address=address1,
        name="RumbleKongLeague",
        num_assets=10000,
        preview_image_url="https://cdn.center.app/1/0xEf0182dc0574cd5874494a120750FD222FdB909a/4205/b75787d89f1204cb9e49293a15e3792ab3b96315ca1c8afb78b82d47bc6f172e.png",
    )
    collection2 = NFTCollection(
        network=network,
        address=address2,
        name="Rumble Kong League Curry Flow",
        num_assets=1278,
        preview_image_url="https://cdn.center.app/1/0x0b87320F22C94e290e763c2F337dC0B44693a548/952/497e8ef8f7ab76542449afc1ceeeded124837ca3d686105383053ad4c5652f2e.png",
    )

    yield Message("bot", f"<|fetch-nft-search({query})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="append", item=collection1),
        StreamingListContainer(operation="append", item=collection2),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(2)),
    ]))

    price = "0.71 ETH"
    token_id1 = "858"
    token_name1 = f"Kong #{token_id1}"
    token_id2 = "1136"
    token_name2 = f"Kong #{token_id2}"
    assets = [
        NFTAsset(
            network=collection1.network,
            address=collection1.address,
            token_id=token_id1,
            collection_name=collection1.name,
            name=token_name1,
            preview_image_url='',
            price=price,
        ),
        NFTAsset(
            network=collection1.network,
            address=collection1.address,
            token_id=token_id2,
            collection_name=collection1.name,
            name=token_name2,
            preview_image_url='',
            price=price,
        ),
    ]
    collection_assets_container = NFTCollectionAssets(
        collection=collection1,
        assets=assets,
    )
    name = "RumbleKongLeague"
    yield Message("user", f"show me NFTs for sale with {name}")
    yield Message("bot", f"<|fetch-nft-collection-assets-for-sale({network},{address1})|>", str(collection_assets_container))
    yield Message("user", f"buy nft {token_id2}")
    yield Message("bot", f"<|fetch-nft-buy-asset({network},{address1},{token_id2})|>", f"<|display-buy-nft({address1},{token_id2})|>")
    yield Message("user", f"set nft {token_id2} as avatar for {domain}")
    yield Message("bot", f"<|set-ens-avatar-nft({domain},{address1},{token_id2})|>")


def get_aave_flow() -> Iterable[Message]:
    amount = 1
    token = "ETH"
    yield Message("user", f"deposit {amount} {token} into Aave")
    yield Message("bot", f"<|aave-supply({token},{amount})|>", "A workflow step was presented.")
    amount = 10
    token = "USDC"
    yield Message("user", f"borrow {amount} {token} on Aave")
    yield Message("bot", f"<|aave-borrow({token},{amount})|>", "A workflow step was presented.")
    amount = 2
    token = "USDC"
    yield Message("user", f"repay {amount} {token} on Aave")
    yield Message("bot", f"<|aave-repay({token},{amount})|>", "A workflow step was presented.")
    amount = 0.1
    token = "ETH"
    yield Message("user", f"withdraw {amount} {token} on Aave")
    yield Message("bot", f"<|aave-withdraw({token},{amount})|>", "A workflow step was presented.")


def get_user_agent(model_name="gpt-4", max_tokens=500, temperature=0.7):
    llm = ChatOpenAI(model_name=model_name, 
                     max_tokens=max_tokens, 
                     temperature=temperature,)
    return llm


def sanitize_str(s : str):
    s = s.strip()
    s = s.replace(' ', '')
    return s


def get_auto_flow(widgets : str, system_message : SystemMessage, user_agent : ChatOpenAI) -> Iterable[Message]:
    messages = [system_message] + [HumanMessage(content=widgets)]
    try:
        output = RE_COMMAND.search(user_agent(messages, stop=')|>")]').content + ')|>")]').group(0)
        for (query, widget_command) in eval(output):
            widget_command = sanitize_str(widget_command)
            if widget_command.startswith(WIDGET_START) and widget_command.endswith(WIDGET_END):
                yield Message("user", query.strip())
                yield Message("bot", widget_command.strip())
    except SyntaxError and AttributeError:
        yield Message("user", None)
        yield Message("bot", None)


def get_validation_conversations() -> Iterable[Conversation]:
    yield Conversation(messages=list(get_nft_flow()))
    yield Conversation(messages=list(get_wallet_balance_flow()))
    yield Conversation(messages=list(get_app_info_flow()))
    yield Conversation(messages=list(get_scraped_sites_flow()))
    yield Conversation(messages=list(get_transfer_flow()))
    yield Conversation(messages=list(get_price_flow()))
    yield Conversation(messages=list(get_swap_flow()))
    yield Conversation(messages=list(get_ens_lookup_flow()))
    yield Conversation(messages=list(get_ens_registration_flow()))
    yield Conversation(messages=list(get_aave_flow()))


def get_auto_validation_conversations(widgets : List, system_message : SystemMessage, user_agent : ChatOpenAI) -> Iterable[Conversation]:
    for _ in range(5):
        widgets = random.choices(widgets, k=args.num_widgets)
        yield Conversation(messages=list(get_auto_flow('---\n'.join(widgets), system_message, user_agent)))


def evaluate_chat(chat: chat.BaseChat, auto : bool = False):
    iter = get_validation_conversations()
    if auto:
        system_message = SystemMessage(content=SYSTEM_MESSAGE_AUTOEVAL)
        widgets = WIDGETS.split('---')
        user_agent = get_user_agent(args.model_name)
        iter = get_auto_validation_conversations(widgets, system_message, user_agent)
        
    for conv in iter:
        chat_history = ChatHistory.new(uuid.UUID('da2321e5-8bcf-45e8-bb29-deee71b379cb'))
        for i in range(0, len(conv.messages), 2):
            user_message  = conv.messages[i]
            bot_message = conv.messages[i + 1]
            
            if user_message.raw_payload == None: continue # for autoeval : the user_agent didn't produce valid output
            assert user_message.actor == 'user', user_message
            assert bot_message.actor == 'bot', bot_message

            user_input = user_message.raw_payload
            completion = bot_message.raw_payload  # unprocessed version, expected output
            bot_response = bot_message.payload  # processed version, for history

            # invoke the chat on user input, gather bot output
            bot_output = None
            function_output = None
            message_id = None
            def send_response(response, **kwargs):
                nonlocal bot_output, function_output, message_id
                if message_id is None:
                    message_id = 0  # emulate this to get the correct operations to be used
                if response.actor == 'bot' and response.operation == 'replace':
                    bot_output = response.response
                if response.actor == 'function':
                    function_output = response.response
                return message_id

            chat_history_copy = copy.deepcopy(chat_history)
            chat.receive_input(chat_history_copy, user_input, send_response)
            assert bot_output is not None

            yield (user_input, bot_output, completion)

            # prepare for next round, but use ground truth response instead
            #chat_history.add_interaction(user_input, bot_response)
            chat_history.add_user_message(user_input)
            if function_output is not None:
                # this is not ground truth, but whatever was generated
                # TODO: have ground truth for this
                chat_history.add_function_message(function_output)
            chat_history.add_bot_message(bot_response)  # this is ground truth


def _get_widget_name(output):
    if '(' in output:
        return output.split('(')[0]
    else:
        return None


def _strip_quotes(output):
    return output.replace('"', '').replace("'", "")


def run(args):
    summary = collections.Counter()
    for ci, chat_config in enumerate(chat_configs):
        chat = config.initialize(chat_config)
        counter = collections.Counter()
        pairs = []
        for user_input, prediction, label in evaluate_chat(chat, args.auto):
            print('user input =', user_input)
            print('prediction =', prediction)
            print('label =', label)
            print('---')
            prediction = prediction.strip()
            label = label.strip()
            widget_param_match = _strip_quotes(prediction) == _strip_quotes(label)
            widget_match = _get_widget_name(prediction) == _get_widget_name(label)
            if widget_param_match:
                counter['widget_param_match'] += 1
            if widget_match:
                counter['widget_match'] += 1
            counter['first_token'] += timing.get('first_visible_bot_token')
            counter['total'] += 1
            pairs.append((user_input, prediction, label))
        for k, v in sorted(counter.items()):
            print(f'{k}: {v}')
        for u, p, l in pairs:
            print(f'{u} :: {p} :: {l}')
        summary[f"{ci}/{chat_config['type']}/accuracy/widget"] = counter['widget_match'] / counter['total']
        summary[f"{ci}/{chat_config['type']}/accuracy/widget_param"] = counter['widget_param_match'] / counter['total']
        summary[f"{ci}/{chat_config['type']}/latency"] = counter['first_token'] / counter['total']
        summary[f"{ci}/{chat_config['type']}/total"] = counter['total']
        res_df = pd.DataFrame(pairs, columns=['user input', 'prediction', 'label'])
        name = f"{chat_config['type']}-{chat_config['model_name']}-{chat_config['top_k']}.csv"
        res_df.to_csv(f"autoeval-{name}", index=False) if args.auto else res_df.to_csv(name, index=False)
    for k, v in sorted(summary.items()):
        print(f'{k}: {v: .2f}')


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description='parser to run the script')

    # add arguments
    parser.add_argument('--auto',
                        type=eval,
                        default=False,
                        help='to trigger autoeval')
    parser.add_argument('--model_name',
                        type=str,
                        default="gpt-4",
                        help='OpenAI model to be used for autoeval')
    parser.add_argument('--num_widgets',
                        type=int,
                        default=10,
                        help='for autoeval - # of widgets to choose from')
    args = parser.parse_args()

    run(args)
    