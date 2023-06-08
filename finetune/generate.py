from dataclasses import dataclass
from typing import Iterable, List, Optional, Union
import enum
import random
import uuid

from tools.index_widget import (
    StreamingListContainer,
    _get_result_list_prefix,
)
from integrations.center import (
    NFTCollection, NFTAsset, NFTCollectionAssets, NFTAssetTraits, NFTAssetTraitValue,
)
from chat.base import ChatHistory, ChatMessage

from .dataset import (
    HISTORY_TOKEN_LIMIT,
    Datapoint,
    save_datapoints,
)


NUM_DATAPOINTS = 500


@dataclass
class Message:
    actor: str
    raw_payload: str
    eval_payload: Optional[str] = None

    @property
    def payload(self):
        if self.actor == 'user':
            payload = self.raw_payload
            # add capitalization perturbation for initial char
            if rf() < 0.5:
                return payload[:1].upper() + payload[1:]
            else:
                return payload
        return self.eval_payload if self.eval_payload is not None else self.raw_payload


def stream_to_str(stream: List) -> str:
    return "\n".join(map(str, stream))


@dataclass
class Conversation:
    messages: List[Message]


def rf():
    return random.random()


def random_network() -> str:
    return random.choice(["ethereum-mainnet", "polygon-mainnet"])


def random_address() -> str:
    return "0x" + "".join(random.choices("0123456789abcdefABCDEF", k=32))


def random_name(with_adjective=False) -> str:
    l = random.randint(4, 15)
    name = "".join(random.choices("0123456789abcdefghijklmnopqrstuvwyxzABCDEFGHIJKLMNOPQRSTUVWXYZ -_#", k=l))
    if with_adjective:
        name = random_adjective() + " " + name
    return name


def random_adjective() -> str:
    return random.choice(["big", "small", "lazy", "wild", "cool", "awesome", "crazy"])


def random_token() -> str:
    l = random.randint(2, 6)
    return "".join(random.choices("0123456789abcdefghijklmnopqrstuvwyxzABCDEFGHIJKLMNOPQRSTUVWXYZ", k=l))


def random_weighted_choice(weight_dict):
    choices = list(weight_dict.keys())
    weights = [weight_dict[k] for k in choices]
    flow = random.choices(choices, weights=weights)[0]
    return flow


def perturb(s: str) -> str:
    r = rf()
    if r < 0.4:
        return s.lower()
    return s


def generate_nft_flow() -> Iterable[Message]:
    query = random_name(with_adjective=rf() < 0.5)
    message = random.choice([
        f"find some {query} NFTs",
        f"find {query} NFTs",
        f"show me {query} NFTs",
    ])
    yield Message("user", message)
    stream = [StreamingListContainer(operation="create", prefix="Searching")]
    num = random.randint(0, 12)
    items = []
    for i in range(num):
        network = random_network()
        address = random_address()
        name = random_name()
        num_assets = random.randint(0, 10000)
        preview_image_url = "http://" + random_name()
        items.append(NFTCollection(
            network=network,
            address=address,
            name=name,
            num_assets=num_assets,
            preview_image_url=preview_image_url,
        ))
    for item in items:
        stream.append(StreamingListContainer(operation="append", item=item))
    stream.append(StreamingListContainer(operation="update", prefix=_get_result_list_prefix(num)))
    yield Message("bot", f"<|fetch-nft-search({query})|>", stream_to_str(stream))
    if num == 0 or rf() < 0.1:
        return
    for msg in generate_nft_collection_flow(items=items):
        yield msg


class NFTCollectionFlow(enum.IntEnum):
    collection_assets = 1
    collection_assets_for_sale = 2
    collection_assets_by_trait = 3
    collection_assets_by_trait_for_sale = 4
    collection_traits = 5


def generate_nft_collection_flow(items: Optional[List[NFTCollection]] = None, item: Optional[NFTCollection] = None, depth: Optional[int] = 0) -> Iterable[Message]:
    if depth > 0 and rf() < 0.5:
        return

    original_item = item

    num = len(items)
    if num > 0 and item is None:
        choice = random.randint(0, num - 1)
        item = items[choice]
        items = list(items)
        items.remove(item)

    if item is None:
        return

    name = perturb(item.name)
    flow = random_weighted_choice({
        NFTCollectionFlow.collection_assets: 1,
        NFTCollectionFlow.collection_assets_for_sale: 1,
        NFTCollectionFlow.collection_assets_by_trait: 0,
        NFTCollectionFlow.collection_assets_by_trait_for_sale: 0,
        NFTCollectionFlow.collection_traits: 1,
    })
    if flow == NFTCollectionFlow.collection_assets:
        message = random.choice([
            f"let's look at {name}",
            f"what are the assets of {name}",
            f"what about {name}",
        ] + ([
            "what are the assets",
        ] if original_item is not None else []))
        yield Message("user", message)

        num = random.randint(0, 12)
        assets = []
        for i in range(num):
            token_id = random.randint(1, 9999)
            preview_image_url = "http://" + random_name()
            price = (str(random.randint(1, 1000) / 100) + ' eth') if rf() < 0.5 else None
            assets.append(NFTAsset(
                network=item.network,
                address=item.address,
                token_id=str(token_id),
                collection_name=item.name,
                name=f'Asset #{token_id}',
                preview_image_url=preview_image_url,
                price=price,
            ))
        nft_collection_assets = NFTCollectionAssets(
            collection=item,
            assets=assets,
        )
        yield Message("bot", f"<|fetch-nft-collection-info({item.network},{item.address})|>", str(nft_collection_assets))

        asset = None
        while rf() < 0.5 and len(assets):
            original_asset = asset
            if asset is None or rf() < 0.5:
                asset = random.choice(assets)
            for msg in generate_nft_asset_flow(asset=asset, already_referenced=original_asset is not None):
                yield msg

    elif flow == NFTCollectionFlow.collection_assets_for_sale:
        message = random.choice([
            f"what are the assets of {name} for sale",
            f"which NFT assets of {name} can I buy",
        ] + ([
            "what are the assets for sale",
            "which assets can I buy",
        ] if original_item is not None else []))
        yield Message("user", message)
        yield Message("bot", f"<|fetch-nft-collection-assets-for-sale({item.network},{item.address})|>")
    elif flow == NFTCollectionFlow.collection_traits:
        message = random.choice([
            f"what are the traits of {name}",
        ] + ([
            "what are the traits of the collection",
        ] if original_item is not None else []))
        yield Message("user", message)
        yield Message("bot", f"<|fetch-nft-collection-traits({item.network},{item.address})|>")
    else:
        assert 0, f'unrecognized flow: {flow}'

    if rf() < 0.5:  # stay with current item
        for msg in generate_nft_collection_flow(items=items, item=item, depth=depth+1):
            yield msg
    else:  # switch to a different one
        for msg in generate_nft_collection_flow(items=items, item=None, depth=depth+1):
            yield msg


class NFTAssetFlow(enum.IntEnum):
    asset_traits = 1
    asset_purchase = 2


def generate_nft_asset_flow(asset: NFTAsset, already_referenced: bool):
    flow = random_weighted_choice({
        NFTAssetFlow.asset_traits: 2,
        NFTAssetFlow.asset_purchase: 1,
    })
    if flow == NFTAssetFlow.asset_traits:
        message = random.choice([
            f"let's look at {asset.token_id}",
            f"what are the traits of {asset.token_id}",
        ] + ([
            "let's look at it",
            "what are its traits",
            "what are the traits of this asset",
        ] if already_referenced else []))
        yield Message("user", message)
        values = []
        for _ in range(5):
            values.append(NFTAssetTraitValue(trait=random_name(), value=random_name()))
        nft_asset_traits = NFTAssetTraits(
            asset=asset,
            values=values,
        )
        yield Message("bot", f"<|fetch-nft-asset-traits({asset.network},{asset.address},{asset.token_id})|>", str(nft_asset_traits))
    elif flow == NFTAssetFlow.asset_purchase:
        message = random.choice([
            f"let's buy {asset.token_id}",
            f"is {asset.token_id} for sale",
        ] + ([
            "let's buy it",
            "is it for sale",
            "can I buy it?",
            "purchase this asset",
        ] if already_referenced else []))
        yield Message("user", message)
        yield Message("bot", f"<|fetch-nft-buy-asset({asset.network},{asset.address},{asset.token_id})|>", f"<|display-buy-nft({asset.address},{asset.token_id})|>")


def generate_wallet_balance_flow(token=None) -> Iterable[Message]:
    original_token = token
    if token is None:
        token = random_token()
    message = random.choice([
        f"what's the balance of {token} in my wallet",
        f"what's my balance of {token}",
        f"my {token} balance",
    ] + ([
        f"what about {token}",
        f"and {token}?",
    ] if original_token is not None else []))
    yield Message("user", message)
    balance = random.random() * 10e5
    yield Message("bot", f"<|fetch-my-balance({token})|>", f"{balance}")
    if rf() < 0.3:
        for msg in generate_wallet_balance_flow(token=random_token()):
            yield msg


def generate_app_info_flow() -> Iterable[Message]:
    messages, query, response = random.choice([
        (["what is this app about"], "What is this app about?", "This app helps you to interact with web3 protocols."),
        (["what can you do", "what functions do you provide"], "What can you do with this app?", "This app lets you interact with web3 protocols."),
        (["who are you?"], "Who are you?", "I am an assistant that lets you interact with web3."),
        (["how do i transact", "how do i do transactions"], "How do I perform a transaction?", "Connect your wallet and interact with the widget."),
        (["what sort of transactions do you support", "what transactions"], "What transactions can you do?", "There are many operations possible."),
    ])
    message = random.choice(messages)
    yield Message("user", message)
    yield Message("bot", f"<|fetch-app-info({query})|>", f"{response}")
    if rf() < 0.2:
        for msg in generate_app_info_flow():
            yield msg


def generate_scraped_sites_flow() -> Iterable[Message]:
    messages, query, response = random.choice([
        (["what is web3"], "Explain web3", "Web3 is a term describing decentralized protocols."),
        (["why do I need a wallet", "what use is a wallet"], "Why is a wallet necessary?", "Wallets allow you to interact with web3."),
        (["what borrowing protocols are out there?"], "What are the protocols available for borrowing?", "There are a few protocols available for borrowing."),
        (["can I use $UNI collateral on aave?"], "Can $UNI collateral be used on AAVE?", "Maybe."),
        (["what is the staking reward for Balancer"], "What is the staking reward for Balancer?", "Unknown."),
    ])
    message = random.choice(messages)
    yield Message("user", message)
    yield Message("bot", f"<|fetch-scraped-sites({query})|>", f"{response}")
    if rf() < 0.2:
        for msg in generate_scraped_sites_flow():
            yield msg


def generate_gather_more_info_flow() -> Iterable[Message]:
    messages, response = random.choice([
        (["buy NFT", "search NFT", "find NFT"], "What kind of NFTs are you looking for?"),
        (["wallet balance", "token balance", "how many tokens"], "Which token would you like to check your balance for?"),
    ])
    message = random.choice(messages)
    yield Message("user", message)
    yield Message("bot", f"{response}")
    if rf() < 0.3:
        for msg in generate_gather_more_info_flow():
            yield msg


class MessageFlow(enum.IntEnum):
    nft = 1
    wallet_balance = 2
    app_info = 3
    scraped_sites = 4
    gather_more_info = 5


def generate_conversation() -> Iterable[Message]:
    count = 0
    while count == 0 or count < 5 and rf() < 0.5:
        count += 1

        flow = random_weighted_choice({
            MessageFlow.nft: 10,
            MessageFlow.wallet_balance: 2,
            MessageFlow.app_info: 2,
            MessageFlow.scraped_sites: 2,
            MessageFlow.gather_more_info: 2,
        })
        if flow == MessageFlow.nft:
            for msg in generate_nft_flow():
                yield msg
        elif flow == MessageFlow.wallet_balance:
            for msg in generate_wallet_balance_flow():
                yield msg
        elif flow == MessageFlow.app_info:
            for msg in generate_app_info_flow():
                yield msg
        elif flow == MessageFlow.scraped_sites:
            for msg in generate_scraped_sites_flow():
                yield msg
        elif flow == MessageFlow.gather_more_info:
            for msg in generate_gather_more_info_flow():
                yield msg
        else:
            assert 0, f'unrecognized flow: {flow}'


def generate_dataset():
    conversations = []
    for _ in range(NUM_DATAPOINTS):
        conversations.append(Conversation(messages=list(generate_conversation())))

    for conv in conversations:
        chat_history = ChatHistory.new(uuid.UUID('da2321e5-8bcf-45e8-bb29-deee71b379cb'))
        datapoints = []
        for i in range(0, len(conv.messages), 2):
            user_message  = conv.messages[i]
            bot_message = conv.messages[i + 1]

            history_string = chat_history.to_string(token_limit=HISTORY_TOKEN_LIMIT)

            user_input = user_message.payload  # has perturbation
            completion = bot_message.raw_payload  # unprocessed version
            bot_response = bot_message.payload  # processed version
            datapoint_task_info = ""  # TODO: handle this

            chat_history.add_interaction(user_input, bot_response)

            datapoint = Datapoint(
                user_input=user_input,
                history=history_string,
                completion=completion,
                task_info=datapoint_task_info,
            )
            datapoints.append(datapoint)
        if datapoints:
            yield datapoints[-1]  # only yield last one for now, for better balance


def run():
    datapoints = []
    for datapoint in generate_dataset():
        print(datapoint)
        datapoints.append(datapoint)
    save_datapoints(datapoints, 'generated.jsonl')


if __name__ == "__main__":
    random.seed(0)
    run()
