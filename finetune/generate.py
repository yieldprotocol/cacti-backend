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
    NFTCollection,
)
from chat.base import ChatHistory, ChatMessage

from .dataset import (
    HISTORY_TOKEN_LIMIT,
    Datapoint,
    save_datapoints,
)


@dataclass
class Message:
    actor: str
    raw_payload: str
    eval_payload: Optional[str] = None

    @property
    def payload(self):
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


def random_weighted_choice(enum_cls, weight_dict):
    choices = list(enum_cls.__members__.values())
    weights = [weight_dict[k] for k in choices]
    flow = random.choices(choices, weights=weights)[0]
    return flow


def perturb(s: str) -> str:
    r = rf()
    if r < 0.4:
        return s.lower()
    return s


def generate_nft_flow() -> Iterable[Message]:
    query = random_name(with_adjective=True)
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
        preview_image_url = ""
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


NFT_COLLECTION_FLOW_WEIGHTS = {
    NFTCollectionFlow.collection_assets: 1,
    NFTCollectionFlow.collection_assets_for_sale: 1,
    NFTCollectionFlow.collection_assets_by_trait: 0,
    NFTCollectionFlow.collection_assets_by_trait_for_sale: 0,
    NFTCollectionFlow.collection_traits: 1,
}


def generate_nft_collection_flow(items: Optional[List[NFTCollection]] = None, item: Optional[NFTCollection] = None, depth: Optional[int] = 0) -> Iterable[Message]:
    if depth > 0 and rf() < 0.5:
        return

    original_item = item

    num = len(items)
    if num > 0:
        choice = random.randint(0, num - 1)
        item = items[choice]
        remaining_items = list(items)
        remaining_items.remove(item)
        for msg in generate_nft_collection_flow(items=remaining_items, item=item, depth=depth + 1):
            yield msg

    for msg in generate_nft_collection_flow(items=items, item=item, depth=depth+1):
        yield msg

    name = perturb(item.name)
    flow = random_weighted_choice(NFTCollectionFlow, NFT_COLLECTION_FLOW_WEIGHTS)
    if flow == NFTCollectionFlow.collection_assets:
        message = random.choice([
            f"let's look at {name}",
            f"what are the assets of {name}",
            f"what about {name}",
        ] + ([
            "what are the assets",
        ] if original_item is not None else []))
        yield Message("user", message)
        yield Message("bot", f"<|fetch-nft-collection-info({item.network},{item.address})|>")
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


def generate_wallet_balance_flow():
    token = random_token()
    message = random.choice([
        f"what's the balance of {token} in my wallet",
        f"what's my balance of {token}",
        f"my {token} balance",
    ])
    yield Message("user", message)
    yield Message("bot", f"<|fetch-my-balance({token})|>")
    if rf() < 0.5:
        token = random_token()
        message = random.choice([
            f"what about {token}",
            f"and {token}?",
        ])
        yield Message("user", message)
        yield Message("bot", f"<|fetch-my-balance({token})|>")


class MessageFlow(enum.IntEnum):
    nft = 1
    wallet_balance = 2


FLOW_WEIGHTS = {
    MessageFlow.nft: 10,
    MessageFlow.wallet_balance: 2,
}


def generate_conversation(depth: int = 0) -> Iterable[Message]:
    if depth > 0 and rf() < 0.5 or depth > 5:
        return

    for msg in generate_conversation(depth=depth + 1):
        yield msg

    flow = random_weighted_choice(MessageFlow, FLOW_WEIGHTS)
    if flow == MessageFlow.nft:
        for msg in generate_nft_flow():
            yield msg
    elif flow == MessageFlow.wallet_balance:
        for msg in generate_wallet_balance_flow():
            yield msg
    else:
        assert 0, f'unrecognized flow: {flow}'


def generate_dataset():
    conversations = []
    for _ in range(100):
        conversations.append(Conversation(messages=list(generate_conversation())))

    for conv in conversations:
        chat_history = ChatHistory.new(uuid.UUID('da2321e5-8bcf-45e8-bb29-deee71b379cb'))
        datapoints = []
        for i in range(0, len(conv.messages), 2):
            user_message  = conv.messages[i]
            bot_message = conv.messages[i + 1]

            history_string = chat_history.to_string(token_limit=HISTORY_TOKEN_LIMIT)

            user_input = user_message.raw_payload
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
