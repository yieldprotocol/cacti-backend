from typing import Any, Generator, List
from dataclasses import dataclass
from dataclasses_json import dataclass_json
import os

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain.llms import OpenAI
from langchain.text_splitter import CharacterTextSplitter

import index
from chat import (
    ChatVariant,
    new_chat,
)

from eval.base import (
    QuestionAnswerChatExample,
    QuestionAnswerChatPrediction,
)


DATASET_DIR = 'qa_scraped'
OUTPUT_DIR = 'qa_scraped_prediction'


def load_dataset() -> Generator[QuestionAnswerChatExample, None, None]:
    dataset_dir = os.path.join(os.path.dirname(__file__), DATASET_DIR)
    for filename in sorted(os.listdir(dataset_dir)):
        filepath = os.path.join(dataset_dir, filename)
        example = QuestionAnswerChatExample.schema().loads(open(filepath).read())
        yield filename, example


def run() -> None:
    output_dir = os.path.join(os.path.dirname(__file__), OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    for chat_variant in [
            ChatVariant.simple,
            ChatVariant.rephrase,
    ]:
        for filename, example in load_dataset():
            basename, _ = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f'{basename}-variant{chat_variant}.json')
            if os.path.exists(output_path):
                continue
            chat_client = new_chat(chat_variant, show_intermediate_output=False)
            responses: List[str] = []
            for interaction in example.interactions:
                response = chat_client.chat(interaction.input)
                responses.append(response.strip())
            pred = QuestionAnswerChatPrediction(
                chat_variant,
                example,
                responses)
            with open(output_path, 'w') as fo:
                fo.write(pred.to_json())


# Run this with: python3 -m eval.predict
if __name__ == "__main__":
    run()
