import os
from typing import Any

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from .base import BaseChat


TEMPLATE = '''
You are a web3 assistant. You help users use web3 apps, such as Uniswap, AAVE, MakerDao, etc. You assist users in achieving their goals with these protocols, by providing users with relevant information, and creating transactions for users.

To help users, an assistant may display information or dialog boxes using magic commands. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>". When the assistant uses a command, users will see data, an interaction box, or other inline item, not the command. Users cannot use magic commands.

Information to help complete your task:
{task_info}

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


class RephraseChat(BaseChat):
    def __init__(self, docsearch: Any, show_rephrased: bool = True) -> None:
        super().__init__()
        self.prompt = PromptTemplate(
            input_variables=["task_info", "question"],
            template=TEMPLATE,
        )
        self.llm = OpenAI(temperature=0.0)
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
        self.chain.verbose = True
        self.docsearch = docsearch
        self.show_rephrased = show_rephrased

        self.rephrase_prompt = PromptTemplate(
            input_variables=["history", "question"],
            template=REPHRASE_TEMPLATE,
        )
        self.rephrase_chain = LLMChain(llm=self.llm, prompt=self.rephrase_prompt)
        self.rephrase_chain.verbose = True

    def chat(self, userinput: str) -> str:
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
        docs = self.docsearch.similarity_search(question)
        task_info = ''.join([doc.page_content for doc in docs])
        result = self.chain.run({
            "task_info": task_info,
            "question": question,
            "stop": "User",
        })
        self.add_interaction(userinput, result)
        if self.show_rephrased and rephrased and userinput != question:
            result = "I think you're asking: " + question + "\n\n" + result
        return result
