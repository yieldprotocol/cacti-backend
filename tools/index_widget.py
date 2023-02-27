from typing import Any, Optional

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.prompts.base import BaseOutputParser

import registry
import streaming
from .index_lookup import IndexLookupTool


TEMPLATE = '''You are a web3 assistant. You help users use web3 apps, such as Uniswap, AAVE, MakerDao, etc. You assist users in achieving their goals with these protocols, by finding out the information needed to create transactions for users. Your responses should sound natural, helpful, cheerful, and engaging, and you should use easy to understand language with explanations for jargon.

To help users, an assistant may display information or dialog boxes using magic commands. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>". When the assistant uses a command, users will see data, an interaction box, or other inline item, not the command. Users cannot type or use magic commands, so do not tell them to use them. Fill in the command with parameters as inferred from the user input query. If there are missing parameters, prompt for them and do not make assumptions without the user's input. Do not return a magic command unless all parameters are known. Examples are given for illustration purposes, do not confuse them for the user's input. If the widget requires a connected wallet, make sure that is available first. If there is no appropriate widget available, explain the situation and ask for more information. Do not make up a non-existent widget magic command, only use the most appropriate one. Here are the widgets that may match the user input:
---
{task_info}
---

User: {question}
Assistant:'''


@registry.register_class
class IndexWidgetTool(IndexLookupTool):
    """Tool for searching a widget index and figuring out how to respond to the question."""

    _chain: LLMChain

    def __init__(
            self,
            *args,
            **kwargs
    ) -> None:
        prompt = PromptTemplate(
            input_variables=["task_info", "question"],
            template=TEMPLATE,
        )
        new_token_handler = kwargs.get('new_token_handler')
        chain = streaming.get_streaming_chain(prompt, new_token_handler)
        super().__init__(
            *args,
            _chain=chain,
            content_description="widget magic command definitions for users to invoke web3 transactions or live data when the specific user action or transaction is clear. You can look up live prices, wallet balances, do transfers or swaps, or search for NFTs. It cannot help the user with understanding how to use the app or how to perform certain actions.",
            input_description="a standalone query with all relevant contextual details mentioned explicitly without using pronouns in order to invoke the right widget",
            output_description="a summarized answer with relevant magic command for widget, or a question prompt for more information to be provided",
            **kwargs
        )

    def _run(self, query: str) -> str:
        """Query index and answer question using document chunks."""
        task_info = super()._run(query)
        example = {
            "task_info": task_info,
            "question": query,
            "stop": "User",
        }
        result = self._chain.run(example)
        return result.strip()
