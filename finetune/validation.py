import collections
import uuid

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from tools.index_widget import (
    StreamingListContainer,
    _get_result_list_prefix,
)
from integrations.center import (
    NFTCollection, NFTAsset,
)
from chat.base import ChatHistory, ChatMessage
from chat.fine_tuned import (
    format_widgets_for_prompt,
    HISTORY_TOKEN_LIMIT,
    TEMPLATE,
    STOP,
    NO_WIDGET_TOKEN,
)
from .generate import (
    Conversation, Message, StreamingListContainer,
    stream_to_str,
)

MODEL_NAME = 'curie:ft-yield-inc-2023-05-30-20-19-41'
#MODEL_NAME = 'curie:ft-yield-inc:truncate-task-info-2023-06-01-00-37-29'
#MODEL_NAME = 'curie:ft-macro-2023-06-06-07-03-08'
MODEL_NAME = 'curie:ft-yield-inc-2023-06-06-07-37-06'
MAX_TOKENS = 200


query = "penguin"
ETH_NETWORK = "ethereum-maintnet"
network1 = ETH_NETWORK
address1 = "0xBd3531dA5CF5857e7CfAA92426877b022e612cf8"
name1 = "PudgyPenguins"
network2 = ETH_NETWORK
address2 = "0x31F3bba9b71cB1D5e96cD62F0bA3958C034b55E9"
name2 = "Party Penguins"
token_id = "1234"
token_name = "Asset #1234"
price = "1.2 ETH"


validation_conversations = [
    Conversation(
        messages=[
            Message("user", f"find some {query} NFTs"),
            Message("bot", f"<|fetch-nft-search({query})|>", stream_to_str([
                StreamingListContainer(operation="create", prefix="Searching"),
                StreamingListContainer(operation="append", item=NFTCollection(
                    network=f"{network1}",
                    address=f"{address1}",
                    name=f"{name1}",
                    num_assets="{num_assets1}",
                    preview_image_url="{preview_image_url1}",
                )),
                StreamingListContainer(operation="append", item=NFTCollection(
                    network=f"{network2}",
                    address=f"{address2}",
                    name=f"{name2}",
                    num_assets="{num_assets2}",
                    preview_image_url="{preview_image_url1}",
                )),
                StreamingListContainer(operation="update", prefix=_get_result_list_prefix(2))
            ])),
            Message("user", f"let's look at {name2}"),
            Message("bot", f"<|fetch-nft-collection-info({network2},{address2})|>"),
            Message("user", f"what are the assets for sale for this collection"),
            Message("bot", f"<|fetch-nft-collection-assets-for-sale({network2},{address2})|>", stream_to_str([
                StreamingListContainer(operation="create", prefix="Searching"),
                StreamingListContainer(operation="append", item=NFTAsset(
                    network=f"{network2}",
                    address=f"{address2}",
                    collection_name=f"{name2}",
                    token_id=f"{token_id}",
                    name=f"{token_name}",
                    preview_image_url="{preview_image_url1}",
                    price=f"{price}",
                )),
            ])),
            Message("user", f"what are the traits for this asset"),
            Message("bot", f"<|fetch-nft-asset-traits({network2},{address2},{token_id})|>"),
            Message("user", f"what are the traits for this collection"),
            Message("bot", f"<|fetch-nft-collection-traits({network2},{address2})|>"),
        ],
    ),
]


def generate_validation_dataset():
    from finetune.dataset import Datapoint

    for conv in validation_conversations:
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
        for datapoint in datapoints:
            yield datapoint


def get_chain():
    prompt = PromptTemplate(
        input_variables=["task_info", "chat_history", "user_input"],
        template=TEMPLATE,
    )
    llm = OpenAI(
        temperature=0.0,
        max_tokens=MAX_TOKENS,
        model_name=MODEL_NAME,
    )
    return LLMChain(llm=llm, prompt=prompt, verbose=True)


def run():
    chain = get_chain()

    counter = collections.Counter()

    results = []
    for datapoint in generate_validation_dataset():
        example = {
            "task_info": datapoint.task_info,
            "chat_history": datapoint.history,
            "user_input": datapoint.user_input,
            "stop": [STOP],
        }
        result = chain.run(example).strip()
        if result == datapoint.completion:
            counter['match'] += 1
        else:
            counter['no_match'] += 1
        results.append((datapoint.completion, result))

    print(counter)
    for row in results:
        print(row)


if __name__ == "__main__":
    run()
