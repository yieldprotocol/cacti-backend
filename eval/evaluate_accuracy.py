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
    QuestionAnswerChatAccuracyEvaluation,
)
import utils


PREDICTION_DIR = 'qa_scraped_prediction'
OUTPUT_DIR = 'qa_scraped_eval_accuracy'



TEMPLATE = '''You are given a few paragraphs of content, a question and a model answer. You have to evaluate (yes/no/unclear) if an alternative answer also accurately answers the same question.

## Begin context
Ethereum is a decentralized, open-source blockchain with smart contract functionality. Ether is the native cryptocurrency of the platform. Among cryptocurrencies, ether is second only to bitcoin in market capitalization.

Ethereum was conceived in 2013 by programmer Vitalik Buterin. Ethereum allows anyone to deploy permanent and immutable decentralized applications onto it, with which users can interact. Decentralized finance (DeFi) applications provide a broad array of financial services without the need for typical financial intermediaries like brokerages, exchanges, or banks, such as allowing cryptocurrency users to borrow against their holdings or lend them out for interest.

On 15 September 2022, Ethereum transitioned its consensus mechanism from proof-of-work (PoW) to proof-of-stake (PoS) in an upgrade process known as "the Merge". This has cut Ethereum's energy usage by 99%.
## End context
Question: What does Ethereum let you do?
Model Answer: Ethereum allows anyone to deploy permanent and immutable decentralized applications onto it.
Alternate Answer: Ethereum is a decentralized, open-source platform that enables the creation and execution of smart contracts and decentralized applications (dApps).
Evaluation: yes

## Begin context
{context}
## End context
Question: {question}
Model Answer: {model_response}
Alternate Answer: {prediction_response}
Evaluation:'''


print('token length of template =', utils.get_token_len(TEMPLATE))


class AccuracyEvaluator:
    def __init__(self) -> None:
        self.prompt = PromptTemplate(
            input_variables=["context", "question", "model_response", "prediction_response"],
            template=TEMPLATE,
        )
        self.llm = OpenAI(temperature=0.0)
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
        self.chain.verbose = True

    def evaluate(self, context: str, question: str, model_response: str, prediction_response: str) -> str:
        response = self.chain.run(dict(
            context=context,
            question=question,
            model_response=model_response,
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
    accuracy_evaluator = AccuracyEvaluator()
    output_dir = os.path.join(os.path.dirname(__file__), OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    for filename, prediction in load_prediction():
        output_path = os.path.join(output_dir, filename)
        if os.path.exists(output_path):
            continue

        accuracy_responses: List[str] = []
        context = prediction.example.context
        for interaction, prediction_response in itertools.zip_longest(prediction.example.interactions, prediction.responses):
            if not interaction:
                break
            if not prediction_response:
                accuracy_response = None
            else:
                question = interaction.input
                model_response = interaction.response
                accuracy_response = accuracy_evaluator.evaluate(context, question, model_response, prediction_response)
            accuracy_responses.append(accuracy_response)
        accuracy = QuestionAnswerChatAccuracyEvaluation(
            prediction,
            accuracy_responses,
        )
        with open(output_path, 'w') as fo:
            fo.write(accuracy.to_json())


# Run this with: python3 -m eval.evaluate_accuracy
if __name__ == "__main__":
    run()
