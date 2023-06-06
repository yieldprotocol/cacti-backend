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
    NFTCollectionTraits, NFTCollectionTrait, NFTCollectionTraitValue,
)
from chat.base import ChatHistory, ChatMessage

from .dataset import (
    HISTORY_TOKEN_LIMIT,
    Datapoint,
    save_datapoints,
)


EMPTY_PARAMS_ALLOWED = True
NUM_DATAPOINTS = 1000


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



def handle_empty_params(message):
    if EMPTY_PARAMS_ALLOWED:
        return message
    else:
        # omit the empty params payload and use the eval (text) version
        return Message(message.actor, message.eval_payload)


def stream_to_str(stream: List) -> str:
    return "\n".join(map(str, stream))


@dataclass
class Conversation:
    messages: List[Message]


def rf():  # random float
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


def random_amount():
    return '%.3f' % (rf() * 1000)


def random_adjective() -> str:
    return random.choice(["big", "small", "lazy", "wild", "cool", "awesome", "crazy"])


def random_transfer_verb() -> str:
    return random.choice(["transfer", "send", "give"])


def random_swap_verb() -> str:
    return random.choice(["swap", "uniswap", "exchange"])


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


def generate_nft_flow(query=None) -> Iterable[Message]:
    original_query = query
    verb = random.choice(["find", "find some", "search", "search for", "show", "show me", "buy", "purchase", ""])
    nft = random.choice(["nft", "NFT", "nfts", "NFTs", "non-fungible token", "non-fungible tokens"])
    if query is None:
        query = random_name(with_adjective=rf() < 0.5)
    msg = []
    if verb: msg.append(verb)
    if original_query is None and rf() < 0.1:
        msg.append(nft)
        message = " ".join(msg)
        yield Message("user", message)
        yield handle_empty_params(Message("bot", f"<|fetch-nft-search()|>", "What kind of NFTs are you looking for?"))
        for msg in generate_nft_flow(query=query):
            yield msg
        return
    msg.extend([query, nft] if rf() < 0.5 else [nft, query])
    message = " ".join(msg)
    yield Message("user", message)
    stream = [StreamingListContainer(operation="create", prefix="Searching")]
    num = random.randint(0, 12)
    collections = []
    for i in range(num):
        network = random_network()
        address = random_address()
        name = random_name()
        num_assets = random.randint(0, 10000)
        preview_image_url = "http://" + random_name()
        collections.append(NFTCollection(
            network=network,
            address=address,
            name=name,
            num_assets=num_assets,
            preview_image_url=preview_image_url,
        ))
    for collection in collections:
        stream.append(StreamingListContainer(operation="append", item=collection))
    stream.append(StreamingListContainer(operation="update", prefix=_get_result_list_prefix(num)))
    yield Message("bot", f"<|fetch-nft-search({query})|>", stream_to_str(stream))
    if num == 0 or rf() < 0.1:
        return
    for msg in generate_nft_collection_flow(collections=collections):
        yield msg


class NFTCollectionFlow(enum.IntEnum):
    collection_assets = 1
    collection_assets_for_sale = 2
    collection_assets_by_trait = 3
    collection_assets_by_trait_for_sale = 4
    collection_traits = 5


def generate_nft_collection_flow(collections: Optional[List[NFTCollection]] = None, collection: Optional[NFTCollection] = None, depth: Optional[int] = 0) -> Iterable[Message]:
    if depth > 0 and rf() < 0.5:
        return

    original_collection = collection

    num = len(collections)
    if num > 0 and collection is None:
        choice = random.randint(0, num - 1)
        collection = collections[choice]
        collections = list(collections)
        collections.remove(collection)

    if collection is None:
        return

    num = random.randint(0, 12)
    assets = []
    for i in range(num):
        token_id = random.randint(1, 9999)
        preview_image_url = "http://" + random_name()
        price = (str(random.randint(1, 1000) / 100) + ' eth') if rf() < 0.5 else None
        assets.append(NFTAsset(
            network=collection.network,
            address=collection.address,
            token_id=str(token_id),
            collection_name=collection.name,
            name=f'Asset #{token_id}',
            preview_image_url=preview_image_url,
            price=price,
        ))

    name = perturb(collection.name)
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
        ] if original_collection is not None else []))
        yield Message("user", message)

        nft_collection_assets = NFTCollectionAssets(
            collection=collection,
            assets=assets,
        )
        yield Message("bot", f"<|fetch-nft-collection-info({collection.network},{collection.address})|>", str(nft_collection_assets))

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
        ] if original_collection is not None else []))
        yield Message("user", message)
        assets_for_sale = [asset for asset in assets if asset.price is not None]
        yield Message("bot", f"<|fetch-nft-collection-assets-for-sale({collection.network},{collection.address})|>", stream_to_str([
            StreamingListContainer(operation="create", prefix="Searching"),
        ] + [
            StreamingListContainer(operation="append", item=asset) for asset in assets_for_sale
        ] + [
            StreamingListContainer(operation="update", prefix=_get_result_list_prefix(len(assets_for_sale))),
        ]))

        asset = None
        while rf() < 0.5 and len(assets_for_sale):
            original_asset = asset
            if asset is None or rf() < 0.5:
                asset = random.choice(assets_for_sale)
            for msg in generate_nft_asset_flow(asset=asset, already_referenced=original_asset is not None):
                yield msg

    elif flow == NFTCollectionFlow.collection_traits:
        message = random.choice([
            f"what are the traits of {name}",
        ] + ([
            "what are the traits of the collection",
        ] if original_collection is not None else []))
        yield Message("user", message)

        collection_traits = []
        for _ in range(5):
            trait_name = random_name()
            trait_values = [random_name(), random_name(), random_name()]
            collection_traits.append(NFTCollectionTrait(
                trait=trait_name,
                values=[
                    NFTCollectionTraitValue(trait=trait_value, value=trait_value, count=3, total=12)
                    for trait_value in trait_values
                ],
            ))
        collection_traits_container = NFTCollectionTraits(
            collection=collection,
            traits=collection_traits,
        )

        yield Message("bot", f"<|fetch-nft-collection-traits({collection.network},{collection.address})|>", str(collection_traits_container))

        collection_trait = None
        trait_name = None
        trait_value = None
        while rf() < 0.5 and len(collection_traits):
            original_trait_name = trait_name
            if trait_name is None or rf() < 0.5:
                collection_trait = random.choice(collection_traits)
                trait_name = collection_trait.trait
            trait_value = random.choice(collection_trait.values).value
            for msg in generate_nft_collection_trait_flow(collection=collection, trait_name=trait_name, trait_value=trait_value, already_referenced=original_trait_name == trait_name):
                yield msg

    else:
        assert 0, f'unrecognized flow: {flow}'

    if rf() < 0.5:  # stay with current collection
        for msg in generate_nft_collection_flow(collections=collections, collection=collection, depth=depth+1):
            yield msg
    else:  # switch to a different one
        for msg in generate_nft_collection_flow(collections=collections, collection=None, depth=depth+1):
            yield msg


def generate_nft_collection_trait_flow(collection: NFTCollection, trait_name: str, trait_value: str, already_referenced: bool):
    message = random.choice([
        f"what assets of the collection have trait {trait_name} and value {trait_value}",
        f"what are all the assets that have the value {trait_value} for {trait_name}?",
        f"which NFTs have {trait_value} for the trait {trait_name}?",
        f"which assets of {collection.name} have the trait {trait_name} as {trait_value}",
    ] + ([
        f"what about {trait_value}?",
        f"which have {trait_value}?",
    ] if already_referenced else []))
    yield Message("user", message)

    yield Message("bot", f"<|fetch-nft-collection-assets-by-trait({collection.network},{collection.address},{trait_name},{trait_value})|>", stream_to_str([
        StreamingListContainer(operation="create", prefix="Searching"),
        StreamingListContainer(operation="update", prefix=_get_result_list_prefix(0)),
    ]))


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
    name = random_name()
    messages, query, response = random.choice([
        (["what is this app about"], "What is this app about?", "This app helps you to interact with web3 protocols."),
        (["what can you do", "what functions do you provide"], "What can you do with this app?", "This app lets you interact with web3 protocols."),
        (["who are you?"], "Who are you?", "I am an assistant that lets you interact with web3."),
        (["how do i transact", "how do i do transactions"], "How do I perform a transaction?", "Connect your wallet and interact with the widget."),
        (["what sort of transactions do you support", "what transactions"], "What transactions can you do?", "There are many operations possible."),
        ([f"can you do {name}", f"is {name} something you can do?"], f"Can you do {name}?", "Yes I can."),
    ])
    message = random.choice(messages)
    yield Message("user", message)
    yield Message("bot", f"<|fetch-app-info({query})|>", f"{response}")
    if rf() < 0.2:
        for msg in generate_app_info_flow():
            yield msg


def generate_scraped_sites_flow() -> Iterable[Message]:
    name = random_name()
    token = random_token()
    messages, query, response = random.choice([
        ([f"what is {name}"], f"Explain {name}", f"{name} is a term describing decentralized protocols."),
        ([f"why do I need a {name}", f"what use is a {name}"], f"Why is a {name} necessary?", f"{name} allows you to interact with web3."),
        ([f"what {name} protocols are out there?"], f"What are the protocols available for {name}?", f"There are a few protocols available for {name}."),
        ([f"can I use {token} collateral on {name}?"], f"Can {token} collateral be used on {name}?", "Maybe."),
        ([f"what is the staking reward for {name}"], f"What is the staking reward for {name}?", "Unknown."),
    ])
    message = random.choice(messages)
    yield Message("user", message)
    yield Message("bot", f"<|fetch-scraped-sites({query})|>", f"{response}")
    if rf() < 0.2:
        for msg in generate_scraped_sites_flow():
            yield msg


def generate_gather_more_info_flow() -> Iterable[Message]:
    messages, command, response = random.choice([
        (["buy NFT", "search NFT", "find NFT"], "<|fetch-nft-search()|>", "What kind of NFTs are you looking for?"),
        (["what's my balance", "wallet balance", "token balance", "how many tokens"], "<|fetch-my-balance()|>", "Which token would you like to check your balance for?"),
        (["price", "live price", "fetch price"], "<|fetch-price()|>", "Which token would you like to check the price of?"),
        ([random_transfer_verb()], "<|display-transfer(,,)|>", "What token would you like to transfer and to which address?"),
    ])
    message = random.choice(messages)
    yield Message("user", message)
    yield handle_empty_params(Message("bot", command, response))
    if rf() < 0.3:
        for msg in generate_gather_more_info_flow():
            yield msg


def generate_transfer_flow(token=None, address=None, amount=None) -> Iterable[Message]:
    ambiguous_fields = []
    if address is None: ambiguous_fields.append('address')
    if amount is None: ambiguous_fields.append('amount')
    if token is None: ambiguous_fields.append('token')
    if len(ambiguous_fields) == 0:
        specified_fields = ['address', 'amount', 'token']
        random.shuffle(specified_fields)
        specified_fields = specified_fields[:random.randint(1, len(specified_fields))]
        message = random_transfer_verb() if rf() < 0.2 else random.choice(["how about", "and", ""])
        if 'amount' in specified_fields:
            amount = random_amount()
            message += f" {amount}"
        if 'token' in specified_fields:
            token = random_token()
            message += random.choice(["", " of"])
            message += f" {token}"
        if 'address' in specified_fields:
            address = random_address()
            message += f" to {address}"
        yield Message("user", message.strip())
        yield Message("bot", f"<|display-transfer({token},{amount},{address})|>")
        if rf() < 0.5:
            for msg in generate_transfer_flow(token=token, address=address, amount=amount):
                yield msg
        return
    random.shuffle(ambiguous_fields)
    specified_fields = ambiguous_fields[:random.randint(1, len(ambiguous_fields))]
    remaining_ambiguous_fields = set(ambiguous_fields) - set(specified_fields)
    message = random_transfer_verb() if len(ambiguous_fields) == 3 or rf() < 0.6 else ""
    if 'amount' in specified_fields:
        amount = random_amount()
        message += f" {amount}"
    if 'token' in specified_fields:
        token = random_token()
        message += random.choice(["", " of"])
        message += f" {token}"
    if 'address' in specified_fields:
        address = random_address()
        message += f" to {address}"
    yield Message("user", message.strip())
    if len(remaining_ambiguous_fields) == 0:
        yield Message("bot", f"<|display-transfer({token},{amount},{address})|>")
        if rf() < 0.5:
            for msg in generate_transfer_flow(token=token, address=address, amount=amount):
                yield msg
    elif len(remaining_ambiguous_fields) == 1:
        if 'token' in remaining_ambiguous_fields:
            yield handle_empty_params(Message("bot", f"<|display-transfer(,{amount},{address})|>", f"Which token would you like to transfer {amount} of to {address}?"))
        elif 'amount' in remaining_ambiguous_fields:
            yield handle_empty_params(Message("bot", f"<|display-transfer({token},,{address})|>", f"What amount of {token} would you like to transfer to {address}?"))
        elif 'address' in remaining_ambiguous_fields:
            yield handle_empty_params(Message("bot", f"<|display-transfer({token},{amount},)|>", f"Which address would you like to transfer {amount} of {token} to?"))
        for msg in generate_transfer_flow(token=token, address=address, amount=amount):
            yield msg
    elif len(remaining_ambiguous_fields) == 2:
        if 'token' not in remaining_ambiguous_fields:
            yield handle_empty_params(Message("bot", f"<|display-transfer({token},,)|>", f"What quantity of {token} would you like to transfer, and to which address?"))
        elif 'amount' not in remaining_ambiguous_fields:
            yield handle_empty_params(Message("bot", f"<|display-transfer(,{amount},)|>", f"Which token would you like to transfer {amount} of, and to which address?"))
        elif 'address' not in remaining_ambiguous_fields:
            yield handle_empty_params(Message("bot", f"<|display-transfer(,,{address})|>", f"Which token would you like to transfer to {address}, and what quantity?"))
        for msg in generate_transfer_flow(token=token, address=address, amount=amount):
            yield msg


def generate_price_flow(base_token=None, quote_token=None) -> Iterable[Message]:
    original_base_token = base_token
    original_quote_token = quote_token
    if base_token is None:
        base_token = random_token()
    if quote_token is None and rf() < 0.5:
        quote_token = random_token()
    message = random.choice([
        f"what's the price of {base_token}",
        f"what is the price of {base_token}",
        f"price {base_token}",
        f"price of {base_token}",
        f"{base_token} price",
    ] + (
        [f"what about {base_token}", f"how about {base_token}"] if original_quote_token is not None else []
    ) + (
        [f"what about", f"how about"] if original_base_token is not None else []
    ))
    if original_quote_token is not None and rf() < 0.5 or quote_token:
        message += random.choice([f" in {quote_token}", f" in units of {quote_token}"])
    message += "?"
    yield Message("user", message)
    price = random_amount()
    if quote_token is None:
        yield Message("bot", f"<|fetch-price({base_token})|>", f"{price}")
    else:
        yield Message("bot", f"<|fetch-price({base_token},{quote_token})|>", f"{price}")
    if rf() < 0.4:
        for msg in generate_price_flow(base_token=base_token, quote_token=quote_token):
            yield msg


def generate_swap_flow(sell_token=None, buy_token=None, keyword=None, amount=None) -> Iterable[Message]:
    ambiguous_fields = []
    if sell_token is None: ambiguous_fields.append('sell_token')
    if buy_token is None: ambiguous_fields.append('buy_token')
    if keyword is None: ambiguous_fields.append('keyword')
    if amount is None: ambiguous_fields.append('amount')

    sell_words = ["", " of"]
    buy_words = [" for", " to buy", " buying"]

    if len(ambiguous_fields) == 0:
        specified_fields = ['sell_token', 'buy_token', 'keyword', 'amount']
        random.shuffle(specified_fields)
        specified_fields = specified_fields[:random.randint(1, len(specified_fields))]
        if rf() < 0.2:
            message = random_swap_verb()
        else:
            message = random.choice(["how about", "and", ""])
            if 'sell_token' in specified_fields or keyword == 'SELLAMOUNT' and 'amount' in specified_fields:
                message += random.choice([random_swap_verb()] + [" sell", " selling"])
        if 'keyword' in specified_fields:
            keyword = random.choice(['SELLAMOUNT', 'BUYAMOUNT'])
        if 'amount' in specified_fields:
            amount = random_amount()
        if keyword == 'SELLAMOUNT' and 'amount' in specified_fields:
            message += f" {amount}"
            if 'sell_token' not in specified_fields:
                message += random.choice(sell_words)
                message += f" {sell_token}"
        if 'sell_token' in specified_fields:
            sell_token = random_token()
            message += random.choice(sell_words)
            message += f" {sell_token}"
        if 'buy_token' in specified_fields or keyword == 'BUYAMOUNT' and 'amount' in specified_fields:
            message += random.choice(buy_words)
        if keyword == 'BUYAMOUNT' and 'amount' in specified_fields:
            message += f" {amount}"
            if 'buy_token' not in specified_fields:
                message += f" {buy_token}"
        if 'buy_token' in specified_fields:
            buy_token = random_token()
            message += f" {buy_token}"
        yield Message("user", message.strip())
        yield Message("bot", f"<|display-uniswap({sell_token},{buy_token},{keyword},{amount})|>")
        if rf() < 0.5:
            for msg in generate_swap_flow(sell_token=sell_token, buy_token=buy_token, keyword=keyword, amount=amount):
                yield msg
        return
    while True:
        random.shuffle(ambiguous_fields)
        specified_fields = ambiguous_fields[:random.randint(1, len(ambiguous_fields))]
        remaining_ambiguous_fields = set(ambiguous_fields) - set(specified_fields)
        if 'keyword' in specified_fields and 'amount' in remaining_ambiguous_fields:
            # can't have keyword specified without an amount
            continue
        if 'amount' in specified_fields and 'keyword' in remaining_ambiguous_fields:
            # can't have amount specified without a keyword
            continue
        break
    message = random_swap_verb() if len(ambiguous_fields) == 4 or rf() < 0.6 or 'sell_token' in specified_fields else ""
    if 'keyword' in specified_fields:
        keyword = random.choice(['SELLAMOUNT', 'BUYAMOUNT'])
    if 'amount' in specified_fields:
        amount = random_amount()
    if keyword == 'SELLAMOUNT' and 'amount' in specified_fields:
        message += f" {amount}"
        if 'sell_token' not in specified_fields and sell_token is not None:
            message += random.choice(sell_words)
            message += f" {sell_token}"
    if 'sell_token' in specified_fields:
        sell_token = random_token()
        if not message.startswith("sell"):
            message += random.choice(sell_words)
        message += f" {sell_token}"
    if 'buy_token' in specified_fields:
        message += random.choice(buy_words)
    if keyword == 'BUYAMOUNT' and 'amount' in specified_fields:
        message += f" {amount}"
        if 'buy_token' not in specified_fields and buy_token is not None:
            message += f" {buy_token}"
    if 'buy_token' in specified_fields:
        buy_token = random_token()
        message += f" {buy_token}"
    yield Message("user", message.strip())
    if len(remaining_ambiguous_fields) == 0:
        yield Message("bot", f"<|display-uniswap({sell_token},{buy_token},{keyword},{amount})|>")
        if rf() < 0.5:
            for msg in generate_swap_flow(sell_token=sell_token, buy_token=buy_token, keyword=keyword, amount=amount):
                yield msg
    else:
        message = "I need more details to complete your swap."
        command = "<|display-uniswap("
        if 'sell_token' in remaining_ambiguous_fields:
            message += " Which token would you like to sell?"
        else:
            command += sell_token
        command += ","
        if 'buy_token' in remaining_ambiguous_fields:
            message += " Which token would you like to buy?"
        else:
            command += buy_token
        command += ","
        if 'amount' in remaining_ambiguous_fields:
            message += " How much would you like to swap?"
        else:
            command += keyword
        command += ","
        if 'keyword' in remaining_ambiguous_fields:
            message += " Which token is represented by the amount?"
        else:
            command += amount
        command += ")|>"
        yield handle_empty_params(Message("bot", command, message))
        for msg in generate_swap_flow(sell_token=sell_token, buy_token=buy_token, keyword=keyword, amount=amount):
            yield msg


class MessageFlow(enum.IntEnum):
    nft = 1
    wallet_balance = 2
    app_info = 3
    scraped_sites = 4
    gather_more_info = 5
    transfer = 6
    price = 7
    swap = 8


def generate_conversation() -> Iterable[Message]:
    count = 0
    while count == 0 or count < 5 and rf() < 0.5:
        count += 1

        flow = random_weighted_choice({
            MessageFlow.nft: 10,
            MessageFlow.wallet_balance: 2,
            MessageFlow.app_info: 2,
            MessageFlow.scraped_sites: 2,
            #MessageFlow.gather_more_info: 2,
            MessageFlow.transfer: 6,
            MessageFlow.price: 3,
            MessageFlow.swap: 6,
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
        elif flow == MessageFlow.transfer:
            for msg in generate_transfer_flow():
                yield msg
        elif flow == MessageFlow.price:
            for msg in generate_price_flow():
                yield msg
        elif flow == MessageFlow.swap:
            for msg in generate_swap_flow():
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
        for datapoint in datapoints:
            yield datapoint


def run():
    datapoints = []
    for datapoint in generate_dataset():
        #print(datapoint)
        datapoints.append(datapoint)
    save_datapoints(datapoints, 'generated.jsonl')


if __name__ == "__main__":
    random.seed(0)
    run()
