# This chat variant determines if the user's query is related to a widget or a search

import os
from typing import Any

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from .base import BaseChat


WIDGET_INSTRUCTION = '''To help users, an assistant may display information or dialog boxes using magic commands. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>". When the assistant uses a command, users will see data, an interaction box, or other inline item, not the command. Users cannot use magic commands. Fill in the command with parameters as inferred from the user input query. Here are the widgets that may match the user input:'''

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
    def __init__(self, doc_search: Any, widget_search: Any, top_k: int = 4, show_thinking: bool = True) -> None:
        super().__init__()
        self.prompt = PromptTemplate(
            input_variables=["instruction", "task_info", "question"],
            template=TEMPLATE,
        )
        self.llm = OpenAI(temperature=0.0, max_tokens=-1)
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
        self.chain.verbose = True
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

    def chat(self, userinput: str) -> str:
        userinput = userinput.strip()
        # First identify the question
        history_string = ""
        for interaction in self.history:
            history_string += ("User: " + interaction.input + "\n")
            history_string += ("Assistant: " + interaction.response + "\n")
        response = self.identify_chain.run({
            "history": history_string.strip(),
            "question": userinput,
            "stop": "##",
        }).strip()
        identified_type, question = response.split(' ', 1)

        if identified_type == '<widget>':
            widgets = self.widget_search.similarity_search(question, k=self.top_k)
            task_info = '\n'.join([f'Widget: {widget.page_content}' for widget in widgets])
            instruction = WIDGET_INSTRUCTION
            thinking = "I think you want a widget for: " + question + "."
        else:
            docs = self.doc_search.similarity_search(question, k=self.top_k)
            task_info = '\n'.join([f'Content: {doc.page_content}\nSource: {doc.metadata["url"]}' for doc in docs])
            instruction = SEARCH_INSTRUCTION
            thinking = "I think you're asking: " + question
        result = self.chain.run({
            "instruction": instruction,
            "task_info": task_info,
            "question": question,
            "stop": "User",
        })
        result = result.strip()
        self.add_interaction(userinput, result)
        if self.show_thinking and userinput != question:
            result = thinking + "\n\n" + result
        return result
