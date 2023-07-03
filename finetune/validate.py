import json
import collections
import copy
import uuid
from typing import Iterable

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from integrations.center import (
    NFTCollection, NFTAsset, NFTCollectionAssets, NFTAssetTraits, NFTAssetTraitValue,
    NFTCollectionTraits, NFTCollectionTrait, NFTCollectionTraitValue,
)
from chat.base import ChatHistory, ChatMessage
import chat
import config
import utils.timing as timing
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
        top_k=10,
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
    yield Message("bot", f"<|fetch-nft-search(query:{query})|>", stream_to_str([
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
    yield Message("bot", f"<|fetch-nft-collection-info(network:{network2},address:{address2})|>", str(collection_assets_container))

    yield Message("user", f"what are the assets for sale for this collection")

    yield Message("bot", f"<|fetch-nft-collection-assets-for-sale(network:{network2},address:{address2})|>", stream_to_str([
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
    yield Message("bot", f"<|fetch-nft-asset-traits(network:{network2},address:{address2},tokenID:{token_id2})|>", str(asset_traits_container))

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
    yield Message("bot", f"<|fetch-nft-collection-traits(network:{network2},address:{address2})|>", str(collection_traits_container))

    trait_name = 'trait1'
    trait_value = 'value1'
    yield Message("user", f"what are the assets with {trait_value} for {trait_name}?")

    yield Message("bot", f"<|fetch-nft-collection-assets-by-trait(network:{network2},address:{address2},traitName:{trait_name},traitValue:{trait_value})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="append", item=assets[1]),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(1)),
    ]))

    yield Message("user", f"which of these are for sale?")
    yield Message("bot", f"<|fetch-nft-collection-assets-for-sale-by-trait(network:{network2},address:{address2},traitName:{trait_name},traitValue:{trait_value})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(0)),
    ]))

    trait_value2 = 'value2'
    yield Message("user", f"what about assets with {trait_value2}?")
    yield Message("bot", f"<|fetch-nft-collection-assets-for-sale-by-trait(network:{network2},address:{address2},traitName:{trait_name},traitValue:{trait_value2})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="append", item=assets[0]),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(1)),
    ]))

    yield Message("user", f"let's buy this one.")
    yield Message("bot", f"<|fetch-nft-buy-asset(network:{network2},address:{address2},tokenID:{token_id1})|>", f"<|display-buy-nft(address:{address2},token_id:{token_id1})|>")


def get_wallet_balance_flow() -> Iterable[Message]:
    token = "ETH"
    balance = 123.456
    yield Message("user", f"what's my balance of {token}?")
    yield Message("bot", f"<|fetch-my-balance(token:{token})|>", f"{balance}")
    token2 = "USDC"
    balance2 = 654.321
    yield Message("user", f"how about {token2}?")
    yield Message("bot", f"<|fetch-my-balance(token:{token2})|>", f"{balance2}")
    address1 = "0x123456"
    balance3 = 0.123
    yield Message("user", f"what about that in {address1}?")
    yield Message("bot", f"<|fetch-balance(token:{token2},address:{address1})|>", f"{balance3}")
    address2 = "0x789123"
    balance4 = 0.1531
    yield Message("user", f"and {address2}?")
    yield Message("bot", f"<|fetch-balance(token:{token2},address:{address2})|>", f"{balance4}")


def get_app_info_flow() -> Iterable[Message]:
    yield Message("user", f"what can I do in this app?")
    query = "What can this app do?"
    response = "Lots of stuff."
    yield Message("bot", f"<|fetch-app-info(query:{query})|>", f"{response}")
    yield Message("user", f"how do I use this app?")
    query = "How do I interact with this app?"
    response = "Chat with it"
    yield Message("bot", f"<|fetch-app-info(query:{query})|>", f"{response}")


def get_scraped_sites_flow() -> Iterable[Message]:
    yield Message("user", f"who invented Ethereum?")
    query = "Who invented Ethereum?"
    response = "Vitalik."
    yield Message("bot", f"<|fetch-scraped-sites(query:{query})|>", f"{response}")
    yield Message("user", f"What is AAVE")
    query = "What is AAVE?"
    response = "A protocol"
    yield Message("bot", f"<|fetch-scraped-sites(query:{query})|>", f"{response}")


def get_transfer_flow() -> Iterable[Message]:
    token = "ETH"
    address = "0x1234"
    amount = "123"
    yield Message("user", f"transfer {token} to {address}")
    yield handle_empty_params(Message("bot", f"<|display-transfer(token:{token},amount:,address:{address})|>", f"What quantity would you like to transfer?"))
    yield Message("user", f"{amount}")
    yield Message("bot", f"<|display-transfer(token:{token},amount:{amount},address:{address})|>")
    token = "USDC"
    address = "0x4321"
    amount = "456"
    yield Message("user", f"send {amount} of {token} to {address}")
    yield Message("bot", f"<|display-transfer(token:{token},amount:{amount},address:{address})|>")


def get_price_flow() -> Iterable[Message]:
    base_token = "ETH"
    quote_token = "USD"
    yield Message("user", f"what's the price of {base_token}?")
    yield Message("bot", f"<|fetch-price(basetoken:{base_token},quotetoken:{quote_token})|>", "1234")
    quote_token = "USDC"
    yield Message("user", f"what's the price of {base_token} in {quote_token}?")
    yield Message("bot", f"<|fetch-price(basetoken:{base_token},quotetoken:{quote_token})|>", "1235")


def get_swap_flow() -> Iterable[Message]:
    sell_token = "ETH"
    buy_token = "USDC"
    keyword = "SELLAMOUNT"
    amount = 123
    yield Message("user", f"swap {sell_token} for {buy_token}")
    yield handle_empty_params(Message("bot", f"<|display-uniswap(tokenToSell:{sell_token},tokenToBuy:{buy_token},transactionKeyword:,amount:)|>", f"What quantity of tokens would you like to swap?"))
    yield Message("user", f"swap {amount} {sell_token} for {buy_token}")
    yield Message("bot", f"<|display-uniswap(tokenToSell:{sell_token},tokenToBuy:{buy_token},transactionKeyword:{keyword},amount:{amount})|>")
    yield Message("user", f"actually swap {sell_token} for {amount} {buy_token}")
    keyword = "BUYAMOUNT"
    yield Message("bot", f"<|display-uniswap(tokenToSell:{sell_token},tokenToBuy:{buy_token},transactionKeyword:{keyword},amount:{amount})|>")


def get_ens_lookup_flow() -> Iterable[Message]:
    address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    domain = "mydomain"
    yield Message("user", f"ens for {address}")
    yield Message("bot", f"<|ens-from-address(address:{address})|>", domain)
    address = "0x1234567890"
    domain = "abcdef.eth"
    yield Message("user", f"address for {domain}")
    yield Message("bot", f"<|address-from-ens(domain:{domain})|>", address)


def get_ens_registration_flow() -> Iterable[Message]:
    domain = "abcdef.eth"
    yield Message("user", f"register {domain}")
    yield Message("bot", f"<|register-ens-domain(domain:{domain})|>", "A workflow step was presented.")
    yield Message("user", f"set primary ENS name to {domain}")
    yield Message("bot", f"<|set-ens-primary-name(domain:{domain})|>", "A transaction was presented for sending.")
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

    yield Message("bot", f"<|fetch-nft-search(query:{query})|>", stream_to_str([
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
    yield Message("bot", f"<|fetch-nft-collection-assets-for-sale(network:{network},address:{address1})|>", str(collection_assets_container))
    yield Message("user", f"buy nft {token_id2}")
    yield Message("bot", f"<|fetch-nft-buy-asset(network:{network},address:{address1},token_id:{token_id2})|>", f"<|display-buy-nft(address1:{address1},token_id2:{token_id2})|>")
    yield Message("user", f"set nft {token_id2} as avatar for {domain}")
    yield Message("bot", f"<|set-ens-avatar-nft(domain:{domain},address:{address1},token_id:{token_id2})|>")


def get_aave_flow() -> Iterable[Message]:
    amount = 1
    token = "ETH"
    yield Message("user", f"deposit {amount} {token} into Aave")
    yield Message("bot", f"<|aave-supply(token:{token},amount:{amount})|>", "A workflow step was presented.")
    amount = 10
    token = "USDC"
    yield Message("user", f"borrow {amount} {token} on Aave")
    yield Message("bot", f"<|aave-borrow(token:{token},amount:{amount})|>", "A workflow step was presented.")
    amount = 2
    token = "USDC"
    yield Message("user", f"repay {amount} {token} on Aave")
    yield Message("bot", f"<|aave-repay(token:{token},amount:{amount})|>", "A workflow step was presented.")
    amount = 0.1
    token = "ETH"
    yield Message("user", f"withdraw {amount} {token} on Aave")
    yield Message("bot", f"<|aave-withdraw(token:{token},amount:{amount})|>", "A workflow step was presented.")


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


def evaluate_chat(chat: chat.BaseChat):
    for conv in get_validation_conversations():
        chat_history = ChatHistory.new(uuid.UUID('da2321e5-8bcf-45e8-bb29-deee71b379cb'))
        for i in range(0, len(conv.messages), 2):
            user_message  = conv.messages[i]
            bot_message = conv.messages[i + 1]
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

            yield (bot_output, completion)

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


def _get_params(output):
    output = _strip_quotes(output)
    if WIDGET_START in output and WIDGET_END in output:
        params = {}
        output = output.split('(')[1].split(')')[0]
        for s in output.split(','):
            params[s.split(':')[0].strip()] = s.split(':')[1].strip()
        return str(sorted(params.items()))
    else:
        return None


def run():
    summary = collections.Counter()
    for ci, chat_config in enumerate(chat_configs):
        chat = config.initialize(chat_config)
        counter = collections.Counter()
        pairs = []
        for prediction, label in evaluate_chat(chat):
            prediction = prediction.strip()
            label = label.strip()
            widget_param_match = _get_params(prediction) == _get_params(label)
            widget_match = _get_widget_name(prediction) == _get_widget_name(label)
            if widget_param_match:
                counter['widget_param_match'] += 1
            if widget_match:
                counter['widget_match'] += 1
            counter['first_token'] += timing.get('first_visible_bot_token')
            counter['total'] += 1
            pairs.append((prediction, label))
        for k, v in sorted(counter.items()):
            print(f'{k}: {v}')
        for p, l in pairs:
            print(f'{p} :: {l}')
        summary[f"{ci}/{chat_config['type']}/accuracy/widget"] = counter['widget_match'] / counter['total']
        summary[f"{ci}/{chat_config['type']}/accuracy/widget_param"] = counter['widget_param_match'] / counter['total']
        summary[f"{ci}/{chat_config['type']}/latency"] = counter['first_token'] / counter['total']
        summary[f"{ci}/{chat_config['type']}/total"] = counter['total']
    for k, v in sorted(summary.items()):
        print(f'{k}: {v: .2f}')


if __name__ == "__main__":
    run()
