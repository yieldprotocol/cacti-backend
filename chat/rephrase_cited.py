import os
from typing import Any, Generator

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from .base import BaseChat, Response


TEMPLATE = '''
You are a web3 assistant. You help users use web3 apps, such as Uniswap, AAVE, MakerDao, etc. You assist users in achieving their goals with these protocols, by providing users with relevant information, and creating transactions for users. Your responses should sound natural, helpful, cheerful, and engaging, and you should use easy to understand language with explanations for jargon.

Information to help complete your task is below. Only use information below to answer the question, and create a final answer with references ("SOURCES").
If you don't know the answer, just say that you don't know. Don't try to make up an answer.
ALWAYS return a "SOURCES" part in your answer.
-----
{task_info}
-----

User: {question}
Assistant:'''


# TODO: make this few-shot on real examples instead of dummy ones
REPHRASE_TEMPLATE = '''
Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question. You should assume that the question is related to web3.

## Example:

Chat History:
User: Who created Ethereum?
Assistant: Vitalik Buterin
Follow Up Input: What about AAVE?
Standalone question: Who created AAVE?

## Example:

Chat History:
User: Who created Ethereum?
Assistant: Vitalik Buterin
User: What about AAVE?
Assistant: Stani Kulechov
Follow Up Input: When was that?
Standalone question: When were Ethereum and AAVE created?

## Example:

Chat History:
User: Who created Ethereum?
Assistant: Vitalik Buterin
Follow Up Input: What is AAVE?
Standalone question: What is AAVE?

## Example:

Chat History:
User: Who created Ethereum?
Assistant: Vitalik Buterin
User: What is AAVE?
Assistant: AAVE is a decentralized finance protocol that allows users to borrow and lend digital assets. It is a protocol built on Ethereum and is powered by a native token, Aave.
Follow Up Input: Bitoin?
Standalone question: What is Bitcoin?

## Example:

Chat History:
{history}
Follow Up Input: {question}
Standalone question:'''


class RephraseCitedChat(BaseChat):
    def __init__(self, docsearch: Any, top_k: int = 3, show_rephrased: bool = True) -> None:
        super().__init__()
        self.prompt = PromptTemplate(
            input_variables=["task_info", "question"],
            template=TEMPLATE,
        )
        self.llm = OpenAI(temperature=0.0, max_tokens=-1)
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
        self.chain.verbose = True
        self.docsearch = docsearch
        self.top_k = top_k
        self.show_rephrased = show_rephrased

        self.rephrase_prompt = PromptTemplate(
            input_variables=["history", "question"],
            template=REPHRASE_TEMPLATE,
        )
        self.rephrase_chain = LLMChain(llm=self.llm, prompt=self.rephrase_prompt)
        self.rephrase_chain.verbose = True

    def chat(self, userinput: str) -> Generator[Response, None, None]:
        userinput = userinput.strip()
        if self.history:
            # First rephrase the question
            history_string = ""
            for interaction in self.history:
                history_string += ("User: " + interaction.input + "\n")
                history_string += ("Assistant: " + interaction.response + "\n")
            question = self.rephrase_chain.run({
                "history": history_string.strip(),
                "question": userinput,
                "stop": "##",
            }).strip()
            rephrased = True
        else:
            question = userinput
            rephrased = False
        if self.show_rephrased and rephrased and userinput != question:
            yield Response(response="I think you're asking: " + question, still_thinking=True)
        docs = self.docsearch.similarity_search(question, k=self.top_k)
        task_info = '\n'.join([f'Content: {doc.page_content}\nSource: {doc.metadata["url"]}' for doc in docs])
        result = self.chain.run({
            "task_info": task_info,
            "question": question,
            "stop": "User",
        })
        result = result.strip()
        self.add_interaction(userinput, result)
        yield Response(result)
