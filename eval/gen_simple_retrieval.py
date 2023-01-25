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


SCRAPE_DIR = '../../deep-cookie/protocols-scraped_data/lido-documentation'
OUTPUT_DIR = 'qa_lido'


TEMPLATE = '''You are given a few paragraphs of content. You have to extract a sequence of questions on Web3 around it, with corresponding answers. Questions in the series may build upon concepts referenced in previous questions and answers. We want sophisticated questions that probe for deep understanding, not simple fact retrieval questions.

## Begin context
Ethereum is a decentralized, open-source blockchain with smart contract functionality. Ether is the native cryptocurrency of the platform. Among cryptocurrencies, ether is second only to bitcoin in market capitalization.

Ethereum was conceived in 2013 by programmer Vitalik Buterin. Ethereum allows anyone to deploy permanent and immutable decentralized applications onto it, with which users can interact. Decentralized finance (DeFi) applications provide a broad array of financial services without the need for typical financial intermediaries like brokerages, exchanges, or banks, such as allowing cryptocurrency users to borrow against their holdings or lend them out for interest.

On 15 September 2022, Ethereum transitioned its consensus mechanism from proof-of-work (PoW) to proof-of-stake (PoS) in an upgrade process known as "the Merge". This has cut Ethereum's energy usage by 99%.

Formal development of the software underlying Ethereum began in early 2014 through a Swiss company, Ethereum Switzerland GmbH (EthSuisse). The idea of putting executable smart contracts in the blockchain needed to be specified before it could be implemented in software. This work was done by Gavin Wood, then the chief technology officer, in the Ethereum Yellow Paper that specified the Ethereum Virtual Machine. Subsequently, a Swiss non-profit foundation, the Ethereum Foundation (Stiftung Ethereum), was founded. Development was funded by an online public crowd sale from July to August 2014, in which participants bought the Ethereum value token (ether) with another digital currency, bitcoin. While there was early praise for the technical innovations of Ethereum, questions were also raised about its security and scalability.

Ethereum 2.0 (Eth2) was a set of three or more upgrades, also known as "phases", meant to transition the network's consensus mechanism to proof-of-stake, and to scale the network's transaction throughput with execution sharding and an improved EVM architecture.[49] The first of these three upgrades, also known as "phase 0", launched the proof-of-stake Beacon Chain on the 1st of December, 2020.
## End context
Q1: How was Ethereum created?
A1: Ethereum was created by a programmer named Vitalik Buterin in 2013. He proposed the idea of a decentralized platform that would allow for the creation and execution of smart contracts and decentralized applications. Ethereum was developed through a Swiss company, Ethereum Switzerland, and subsequently a Swiss non-profit foundation, the Ethereum Foundation.

Q2: How does it work?
A2: Ethereum works by using a decentralized, open-source blockchain network to enable the creation and execution of smart contracts and decentralized applications (dApps). The Ethereum blockchain is a distributed ledger that keeps track of all transactions and smart contract executions on the network. Each node on the network maintains a copy of the blockchain, and new transactions and smart contract executions are added to the blockchain through a process called mining.

Q3: What is a recent update for the project?
A3: Ethereum transitioned its consensus mechanism from proof-of-work to proof-of-stake on 15 September 2022. This culminates the multiple phases of upgrades beginning 1 December 2020 that together were called Eth2.

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
        self.llm = OpenAI(temperature=0.9, max_tokens=1024)
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
        if filename in (
                'https:__docs.lido.fi_contracts_lido-oracle.txt',
                'https:__docs.lido.fi_lido-dao.txt',
                'https:__docs.lido.fi_.txt',
        ):
            continue
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
    text_splitter = CharacterTextSplitter(chunk_size=4000, chunk_overlap=300)
    gen = QuestionAnswerGenerator()
    output_dir = os.path.join(os.path.dirname(__file__), OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    for scraped_file in iter_files():
        print(scraped_file.filename, len(scraped_file.content))
        docs = text_splitter.split_text(scraped_file.content)
        for context in docs:
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
