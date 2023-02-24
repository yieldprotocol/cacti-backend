# This chat variant uses an agent with access to tools

import os
import time
from typing import Any, Callable, List

from langchain.llms import OpenAI
from langchain.agents import initialize_agent

import registry
from tools.base import BaseTool
from .base import BaseChat, ChatHistory, Response, streaming_callback_manager


@registry.register_class
class BasicAgentChat(BaseChat):
    def __init__(self, tools: List[BaseTool], show_thinking: bool = True) -> None:
        super().__init__()
        self.tools = tools
        self.show_thinking = show_thinking
        self.llm = OpenAI(temperature=0.0, max_tokens=-1)
        self.agent = initialize_agent(self.tools, self.llm, agent="zero-shot-react-description", verbose=True)

    def receive_input(self, history: ChatHistory, userinput: str, send: Callable) -> None:
        userinput = userinput.strip()
        start = time.time()
        result = self.agent.run(userinput)
        duration = time.time() - start
        history.add_interaction(userinput, result)
        send(Response(result))
        send(Response(response=f'Response generation took {duration: .2f}s', actor='system'))
