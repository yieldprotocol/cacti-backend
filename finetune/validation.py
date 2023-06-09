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
)

from .generate import (
    Conversation, Message, StreamingListContainer,
    stream_to_str,
)


chat_configs = [
    dict(
        type='chat.fine_tuned.FineTunedChat',
        widget_index=None,
        #model_name='curie:ft-yield-inc:gen-500-2023-06-08-08-20-51',
        model_name='curie:ft-yield-inc:gen-1k-2023-06-09-18-41-36',
        evaluate_widgets=False,
    ),
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


def get_validation_conversations() -> Iterable[Conversation]:
    yield Conversation(messages=list(get_nft_flow()))
    yield Conversation(messages=list(get_wallet_balance_flow()))
    yield Conversation(messages=list(get_app_info_flow()))
    yield Conversation(messages=list(get_scraped_sites_flow()))


def evaluate_chat(chat: chat.BaseChat):
    for conv in get_validation_conversations():
        chat_history = ChatHistory.new(uuid.UUID('da2321e5-8bcf-45e8-bb29-deee71b379cb'))
        for i in range(0, len(conv.messages), 2):
            user_message  = conv.messages[i]
            bot_message = conv.messages[i + 1]

            user_input = user_message.raw_payload
            completion = bot_message.raw_payload  # unprocessed version, expected output
            bot_response = bot_message.payload  # processed version, for history

            # invoke the chat on user input, gather bot output
            bot_output = None
            message_id = None
            def send_response(response, **kwargs):
                nonlocal bot_output, message_id
                if message_id is None:
                    message_id = 0  # emulate this to get the correct operations to be used
                if response.actor == 'bot' and response.operation == 'replace':
                    bot_output = response.response
                return message_id

            chat_history_copy = copy.deepcopy(chat_history)
            chat.receive_input(chat_history_copy, user_input, send_response)
            assert bot_output is not None

            yield (bot_output, completion)

            # prepare for next round, but use ground truth response instead
            chat_history.add_interaction(user_input, bot_response)



def run():
    summary = collections.Counter()
    for chat_config in chat_configs:
        chat = config.initialize(chat_config)
        counter = collections.Counter()
        pairs = []
        for prediction, label in evaluate_chat(chat):
            prediction = prediction.strip()
            label = label.strip()
            widget_param_match = prediction == label
            widget_match = prediction.split('(')[0] == label.split('(')[0]
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
        summary[chat_config['type'] + '/accuracy/widget'] = counter['widget_match'] / counter['total']
        summary[chat_config['type'] + '/accuracy/widget_param'] = counter['widget_param_match'] / counter['total']
        summary[chat_config['type'] + '/latency'] = counter['first_token'] / counter['total']
        summary[chat_config['type'] + '/total'] = counter['total']
    for k, v in sorted(summary.items()):
        print(f'{k}: {v: .2f}')


if __name__ == "__main__":
    run()
