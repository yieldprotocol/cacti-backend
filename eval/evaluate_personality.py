from typing import Generator, List
from dataclasses import dataclass
from dataclasses_json import dataclass_json
import itertools
import os

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from eval.base import (
    QuestionAnswerChatExample,
    QuestionAnswerChatPrediction,
    QuestionAnswerChatPersonalityEvaluation,
)
import utils


PREDICTION_DIR = 'qa_scraped_prediction'
OUTPUT_DIR = 'qa_scraped_eval_personality'



TEMPLATE = '''You are given a question and an answer. You have to evaluate if the answer to the question is friendly, cheerful, and engaging, and if so, output yes. A good answer is one that not only answers the question, but also responds with sentences that are easy to understand, with explanations for jargon. They should also sound natural, like a human would respond in a casual conversation, instead of having a flat monotonous tone.

## Example
Question: What does Ethereum let you do?
Answer: Ethereum allows anyone to deploy permanent and immutable decentralized applications onto it.
Evaluation: no

## Example
Question: What does Ethereum let you do?
Answer: Ethereum is a decentralized, open-source blockchain with smart contract functionality. It allows anyone to deploy permanent and immutable decentralized applications, also known as dApps, onto it. Smart contracts are self-executing contracts with the terms of the agreement written directly into lines of code. They allow for the automation of a variety of processes, such as the transfer of assets between parties, without the need for intermediaries. dApps are decentralized applications that are built on top of the Ethereum blockchain. They are designed to be censorship-resistant and allow for the creation of decentralized marketplaces, prediction markets, social networks, and more.
Evaluation: yes

## Example
Question: {question}
Answer: {prediction_response}
Engaging:'''


print('token length of template =', utils.get_token_len(TEMPLATE))


class PersonalityEvaluator:
    def __init__(self) -> None:
        self.prompt = PromptTemplate(
            input_variables=["question", "prediction_response"],
            template=TEMPLATE,
        )
        self.llm = OpenAI(temperature=0.0)
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
        self.chain.verbose = True

    def evaluate(self, question: str, prediction_response: str) -> str:
        response = self.chain.run(dict(
            question=question,
            prediction_response=prediction_response,
            stop="##",
        ))
        response = response.strip().lower()
        print(response)
        return response


def load_prediction() -> Generator[QuestionAnswerChatPrediction, None, None]:
    prediction_dir = os.path.join(os.path.dirname(__file__), PREDICTION_DIR)
    for filename in sorted(os.listdir(prediction_dir)):
        filepath = os.path.join(prediction_dir, filename)
        with open(filepath) as fi:
            example = QuestionAnswerChatPrediction.schema().loads(fi.read())
        yield filename, example


def run() -> None:
    personality_evaluator = PersonalityEvaluator()
    output_dir = os.path.join(os.path.dirname(__file__), OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    for filename, prediction in load_prediction():
        output_path = os.path.join(output_dir, filename)
        if os.path.exists(output_path):
            continue

        personality_responses: List[str] = []
        for interaction, prediction_response in itertools.zip_longest(prediction.example.interactions, prediction.responses):
            if not interaction:
                break
            if not prediction_response:
                personality_response = None
            else:
                question = interaction.input
                personality_response = personality_evaluator.evaluate(question, prediction_response)
            personality_responses.append(personality_response)
        personality = QuestionAnswerChatPersonalityEvaluation(
            prediction,
            personality_responses,
        )
        with open(output_path, 'w') as fo:
            fo.write(personality.to_json())


# Run this with: python3 -m eval.evaluate_personality
if __name__ == "__main__":
    run()
