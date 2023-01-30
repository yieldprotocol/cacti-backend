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

Information about the chat so far:
{summary}

Chat History:
{history}
Assistant:'''



class SimpleChat(BaseChat):
    def __init__(self, docsearch: Any, top_k: int = 4) -> None:
        super().__init__()
        self.prompt = PromptTemplate(
            input_variables=["task_info", "summary", "history"],
            template=TEMPLATE,
        )
        self.llm = OpenAI(temperature=0.9, max_tokens=-1)
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
        self.chain.verbose = True
        self.docsearch = docsearch
        self.top_k = top_k

    def chat(self, userinput: str) -> str:
        docs = self.docsearch.similarity_search(userinput, k=self.top_k)
        task_info = ''.join([doc.page_content for doc in docs])
        history_string = ""
        for interaction in self.history:
            history_string += ("User: " + interaction.input + "\n")
            history_string += ("Assistant: " + interaction.response + "\n")
        history_string += ("User: " + userinput )
        result = self.chain.run({
            "task_info": task_info,
            "summary": "",
            "history": history_string,
            "stop": "User",
        })
        result = result.strip()
        self.add_interaction(userinput, result)
        return result
