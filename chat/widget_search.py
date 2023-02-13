# This chat variant determines if the user's query is related to a widget or a search

import os
import time
from typing import Any, Generator

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from .base import BaseChat, Response


WIDGET_INSTRUCTION = '''To help users, an assistant may display information or dialog boxes using magic commands. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>". When the assistant uses a command, users will see data, an interaction box, or other inline item, not the command. Users cannot use magic commands. Fill in the command with parameters as inferred from the user input query. If there are missing parameters, prompt for them and do not make assumptions without the user's input. Do not return a magic command unless all parameters are known. Examples are given for illustration purposes, do not confuse them for the user's input. If a widget involves a transaction that requires user confirmation, prompt for it. If the widget requires a connected wallet, make sure that is available first. If there is no appropriate widget available, explain the situation and ask for more information. Do not make up a non-existent widget magic command, only use the most appropriate one. Here are the widgets that may match the user input:'''

SEARCH_INSTRUCTION = '''Information to help complete your task is below. Only use information below to answer the question, and create a final answer with inline citations linked to the provided source URLs. If you don't know the answer, just say that you don't know. Don't try to make up an answer. ALWAYS return a "SOURCES" part in your answer corresponding to the numbered inline citations.'''


TEMPLATE = '''You are a web3 assistant. You help users use web3 apps, such as Uniswap, AAVE, MakerDao, etc. You assist users in achieving their goals with these protocols, by providing users with relevant information, and creating transactions for users. Your responses should sound natural, helpful, cheerful, and engaging, and you should use easy to understand language with explanations for jargon.

{instruction}
---
{task_info}
---

User: {question}
Assistant:'''


# TODO: make this few-shot on real examples instead of dummy ones
IDENTIFY_TEMPLATE = '''
Given the following conversation and a follow up response input, determine if the input is related to a command to invoke using a widget or if it is a search query for a knowledge base. If it is a widget, return the appropriate keywords to search for the widget, as well as all relevant details to invoke it. If it is a search query, rephrase as a standalone question. You should assume that the query is related to web3.

## Example:

Chat History:
User: I'd like to make transfer ETH
Assistant: Ok I can help you with that. How much and to which address?

Input: 2 ETH to andy
Ouput: <widget> transfer of 2 ETH currency to andy

## Example:

Chat History:
User: Who created Ethereum?
Assistant: Vitalik Buterin
User: What about AAVE?
Assistant: Stani Kulechov

Input: When was that?
Output: <query> When were Ethereum and AAVE created?

## Example:

Chat History:
User: Who created Ethereum?
Assistant: Vitalik Buterin

Input: What is AAVE?
Output: <query> What is AAVE?

## Example:

Chat History:
User: What's my balance of USDC?
Assistant: Your USDC balance is <|balance('USDC')|>

Input: cost of ETH
Output: <widget> price of ETH coin given USDC balance

## Example:

Chat History:
{history}

Input: {question}
Output:'''


class WidgetSearchChat(BaseChat):
    def __init__(self, doc_search: Any, widget_search: Any, top_k: int = 3, show_thinking: bool = True) -> None:
        super().__init__()
        self.widget_prompt = PromptTemplate(
            input_variables=["task_info", "question"],
            template=TEMPLATE.replace("{instruction}", WIDGET_INSTRUCTION),
        )
        self.search_prompt = PromptTemplate(
            input_variables=["task_info", "question"],
            template=TEMPLATE.replace("{instruction}", SEARCH_INSTRUCTION),
        )
        self.llm = OpenAI(temperature=0.0, max_tokens=-1)
        self.widget_chain = LLMChain(llm=self.llm, prompt=self.widget_prompt)
        self.widget_chain.verbose = True
        self.search_chain = LLMChain(llm=self.llm, prompt=self.search_prompt)
        self.search_chain.verbose = True
        self.doc_search = doc_search
        self.widget_search = widget_search
        self.top_k = top_k
        self.show_thinking = show_thinking

        self.identify_prompt = PromptTemplate(
            input_variables=["history", "question"],
            template=IDENTIFY_TEMPLATE,
        )
        self.identify_chain = LLMChain(llm=self.llm, prompt=self.identify_prompt)
        self.identify_chain.verbose = True

    def chat(self, userinput: str) -> Generator[Response, None, None]:
        userinput = userinput.strip()
        # First identify the question
        history_string = ""
        for interaction in self.history:
            history_string += ("User: " + interaction.input + "\n")
            history_string += ("Assistant: " + interaction.response + "\n")
        start = time.time()
        response = self.identify_chain.run({
            "history": history_string.strip(),
            "question": userinput,
            "stop": "##",
        }).strip()
        duration = time.time() - start
        identified_type, question = response.split(' ', 1)

        if self.show_thinking and userinput != question:
            if identified_type == '<widget>':
                thinking = "I think you want a widget for: " + question + "."
            else:
                thinking = "I think you're asking: " + question
            yield Response(response=thinking, still_thinking=True)
        yield Response(response=f'Intent identification took {duration: .2f}s', actor='system')
        if identified_type == '<widget>':
            widgets = self.widget_search.similarity_search(question, k=self.top_k)
            task_info = '\n'.join([f'Widget: {widget.page_content}' for widget in widgets])
            chain = self.widget_chain
        else:
            docs = self.doc_search.similarity_search(question, k=self.top_k)
            task_info = '\n'.join([f'Content: {doc.page_content}\nSource: {doc.metadata["url"]}' for doc in docs])
            chain = self.search_chain
        #yield Response(response=task_info, actor='system')  # TODO: too noisy
        start = time.time()
        result = chain.run({
            "task_info": task_info,
            "question": question,
            "stop": "User",
        })
        duration = time.time() - start
        result = result.strip()
        self.add_interaction(userinput, result)
        yield Response(result)
        yield Response(response=f'Response generation took {duration: .2f}s', actor='system')
