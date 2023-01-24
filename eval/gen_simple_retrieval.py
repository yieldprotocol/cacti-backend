from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Generator, List
import os
import uuid

import tiktoken
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.text_splitter import CharacterTextSplitter

from chat.base import Interaction
from eval.base import ScrapedFile, QuestionAnswerChatExample


os.environ["OPENAI_API_KEY"] = "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"
OpenAI.api_key = "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"


SCRAPE_DIR = '../../deep-cookie/protocols-scraped_data/lido-documentation'
OUTPUT_DIR = 'qa_lido'


TEMPLATE = '''You are given a few paragraphs of content. You have to extract a sequence of questions on Web3 around it, with corresponding answers. Questions in the series may build upon concepts referenced in previous questions and answers.

## Begin context
Ethereum is a decentralized, open-source blockchain with smart contract functionality. Ether is the native cryptocurrency of the platform. Among cryptocurrencies, ether is second only to bitcoin in market capitalization.

Ethereum was conceived in 2013 by programmer Vitalik Buterin. Ethereum allows anyone to deploy permanent and immutable decentralized applications onto it, with which users can interact. Decentralized finance (DeFi) applications provide a broad array of financial services without the need for typical financial intermediaries like brokerages, exchanges, or banks, such as allowing cryptocurrency users to borrow against their holdings or lend them out for interest.

On 15 September 2022, Ethereum transitioned its consensus mechanism from proof-of-work (PoW) to proof-of-stake (PoS) in an upgrade process known as "the Merge". This has cut Ethereum's energy usage by 99%.
## End context
Q1: What does Ethereum let you do?
A1: Ethereum allows anyone to deploy permanent and immutable decentralized applications onto it.

Q2: Who created it?
A2: Vitalik Buterin.

Q3: What is a recent update for the project?
A3: Ethereum transitioned its consensus mechanism from proof-of-work to proof-of-stake on 15 September 2022.

## Begin context
{context}
## End context
Q1:'''


tokenizer = tiktoken.get_encoding("gpt2")
print('token length of template =', len(tokenizer.encode(TEMPLATE)))


class QuestionAnswerGenerator:
    def __init__(self) -> None:
        self.prompt = PromptTemplate(
            input_variables=["context"],
            template=TEMPLATE,
        )
        self.llm = OpenAI(temperature=0.5)
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
        self.chain.verbose = True

    def generate(self, context: str) -> List[Interaction]:
        ret: List[Interaction] = []
        response = self.chain.run(dict(context=context, stop="##"))
        # parse interactions
        response = 'Q1: ' + response.strip()
        lines = response.split('\n')
        #for i, line in enumerate(lines):
        #    print(i, line)
        i = 0
        while i + 1 < len(lines):
            question, answer = lines[i: i + 2]
            # strip Q/A prefix
            question_prefix, question = question.split(':', 1)
            answer_prefix, answer = answer.split(':', 1)
            assert 'Q' in question_prefix and 'A' in answer_prefix, (question, answer)
            ret.append(Interaction(question.strip(), answer.strip()))
            i += 3
        return ret


def iter_files() -> Generator[str, None, None]:
    scrape_dir = os.path.join(os.path.dirname(__file__), SCRAPE_DIR)
    for filename in os.listdir(scrape_dir):
        filepath = os.path.join(scrape_dir, filename)
        lines = list(open(filepath).readlines())
        num_lines = len(lines)
        num_chars = sum(map(len, lines))
        if num_chars < 100:
            continue
        yield ScrapedFile(filename, '\n'.join(lines))


def save_output(output_dir: str, example: QuestionAnswerChatExample) -> None:
    hex = uuid.uuid4().hex
    output_path = os.path.join(output_dir, f'example-{hex}.json')
    with open(output_path, 'w') as fo:
        fo.write(example.to_json())


def run() -> None:
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    gen = QuestionAnswerGenerator()
    output_dir = os.path.join(os.path.dirname(__file__), OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    for scraped_file in iter_files():
        print(scraped_file.filename, len(scraped_file.content))
        docs = text_splitter.split_text(scraped_file.content)
        for context in docs[1:3]:
            print(f'Context:\n{context}')
            interactions = gen.generate(context)
            for i, interaction in enumerate(interactions):
                print(f'Interaction {i}\nQ: {interaction.input}\nA: {interaction.response}')
            example = QuestionAnswerChatExample(scraped_file.filename, context, interactions)
            save_output(output_dir, example)
        break


# Run this with: python3 -m eval.gen_simple_retrieval
if __name__ == "__main__":
    run()
