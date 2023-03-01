from typing import Any, Optional

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.prompts.base import BaseOutputParser

import registry
import streaming
from .index_lookup import IndexLookupTool


TEMPLATE = '''You are a web3 assistant. You help users use web3 apps, such as Uniswap, AAVE, MakerDao, etc. You assist users in achieving their goals with these protocols, by finding out the information needed to create transactions for users. Your responses should sound natural, helpful, cheerful, and engaging, and you should use easy to understand language with explanations for jargon.

To help users, an assistant may delegate work to magic commands. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>". The command may either have a display- or a fetch- prefix. When the assistant returns a display- command, the user will see data, an interaction box, or other inline item rendered in its place. When a fetch- command is used, data is fetched over an API and injected in place. Fetch- commands can be nested in other magic commands, and will be resolved recursively, for example, "<|command1(parameter1, <|command2(parameter2)|>)|>". Simple expressions can be resolved with the "<|fetch-eval(expression)|>" command, for example, the ratio of 2 numbers can be calculated as "<|fetch-eval(number1/number2)|>". Users cannot type or use magic commands, so do not tell them to use them. Fill in the command with parameters as inferred from the user input query. If there are missing parameters, prompt the user for them and do not make assumptions without the user's input. Do not mention a magic command to the user unless you want to invoke or render it. Examples are given for illustration purposes, do not confuse them for the user's input. If the widget requires a connected wallet, make sure the user has already connected their wallet. If there is no appropriate widget available, explain the situation and ask for more information. Do not make up a non-existent widget magic command, only use the applicable ones for the situation. Here are the widgets that may match the user input:
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
            content_description="widget magic command definitions for users to invoke web3 transactions or live data when the specific user action or transaction is clear. You can look up live prices, wallet balances, token contract addresses, do transfers or swaps, or search for NFTs and retrieve data about NFTs. It cannot help the user with understanding how to use the app or how to perform certain actions.",
            input_description="a standalone query phrase with all relevant contextual details mentioned explicitly without using pronouns in order to invoke the right widget",
            output_description="a summarized answer with relevant magic command for widget(s), or a question prompt for more information to be provided",
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
