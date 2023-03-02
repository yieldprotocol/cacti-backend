from typing import Any, Optional

from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.prompts.base import BaseOutputParser

import registry
import streaming
from .index_lookup import IndexLookupTool


TEMPLATE = '''You are a web3 widget tool. You have access to a list of widget magic commands that you can delegate work to, by invoking them and chaining them together, to provide a response to an input query. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>". They can only be used with all parameters having known and assigned values, otherwise, they have to be kept secret. The command may either have a display- or a fetch- prefix. When you return a display- command, the user will see data, an interaction box, or other inline item rendered in its place. When you return a fetch- command, data is fetched over an API and injected in place. Fetch- commands can be nested in other magic commands, and will be resolved recursively, for example, "<|command1(parameter1, <|command2(parameter2)|>)|>". Simple expressions can be resolved with the "<|fetch-eval(expression)|>" command, for example, the ratio of 2 numbers can be calculated as "<|fetch-eval(number1/number2)|>". Users cannot type or use magic commands, so do not tell them to use them. Fill in the command with parameters as inferred from the input. If there are missing parameters, do not use magic commands but mention what parameters are needed instead. If the widget requires a connected wallet that is not available, state that a connected wallet is needed, and don't use any magic commands. If there is no appropriate widget available, explain that more information is needed. Do not make up a non-existent widget magic command, only use the applicable ones for the situation, and only if all parameters are available. You might need to use the output of widget magic commands as the input to another to get your final answer. Here are the widgets that may be relevant:
---
{task_info}
---

Tool input: {question}
Tool response:'''


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
