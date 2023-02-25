# This chat variant uses an agent with access to tools

import os
import time
from typing import Any, Callable, List

import registry
import streaming
from tools.base import BaseTool
from .base import BaseChat, ChatHistory, Response


# We mirror these from langchain/agents/mrkl/prompt.py, so we can modify them
PREFIX = """Answer the following questions as best you can. You have access to the following tools:"""
FORMAT_INSTRUCTIONS = """Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question"""
SUFFIX = """Begin!

Question: {input}
Thought:{agent_scratchpad}"""


@registry.register_class
class BasicAgentChat(BaseChat):
    def __init__(self, tools: List[BaseTool], show_thinking: bool = True) -> None:
        super().__init__()
        self.tools = tools
        self.show_thinking = show_thinking

    def receive_input(self, history: ChatHistory, userinput: str, send: Callable) -> None:
        userinput = userinput.strip()
        start = time.time()

        system_chat_message_id = None
        system_response = ''
        bot_chat_message_id = None
        bot_response = ''

        def system_flush(response):
            nonlocal system_chat_message_id
            send(Response(
                response=response,
                still_thinking=True,
                actor='system',
                operation='replace',
            ), last_chat_message_id=system_chat_message_id)

        def bot_flush(response):
            nonlocal bot_chat_message_id
            send(Response(
                response=response,
                still_thinking=False,
                actor='bot',
                operation='replace',
            ), last_chat_message_id=bot_chat_message_id)

        def system_new_token_handler(token):
            nonlocal system_chat_message_id, system_response, bot_chat_message_id, bot_response

            if bot_chat_message_id is not None:
                bot_flush(bot_response)
                bot_chat_message_id = None
                bot_response = ''

            system_response += token
            system_chat_message_id = send(Response(
                response=token,
                still_thinking=True,
                actor='system',
                operation='append' if system_chat_message_id is not None else 'create',
            ), last_chat_message_id=system_chat_message_id)

        def bot_new_token_handler(token):
            nonlocal bot_chat_message_id, bot_response, system_chat_message_id, system_response

            if system_chat_message_id is not None:
                system_flush(system_response)
                system_chat_message_id = None
                system_response = ''

            bot_response += token
            bot_chat_message_id = send(Response(
                response=token,
                still_thinking=False,
                actor='bot',
                operation='append' if bot_chat_message_id is not None else 'create',
            ), last_chat_message_id=bot_chat_message_id)

        tools = streaming.get_streaming_tools(self.tools, bot_new_token_handler)
        agent = streaming.get_streaming_agent(
            tools,
            system_new_token_handler,
            prefix=PREFIX,
            suffix=SUFFIX,
            format_instructions=FORMAT_INSTRUCTIONS,
        )
        result = agent.run(userinput)
        duration = time.time() - start
        history.add_interaction(userinput, result)

        if system_chat_message_id is not None:
            system_flush(system_response)

        if bot_chat_message_id is not None:
            bot_flush(result)
        else:
            send(Response(response=result))

        send(Response(response=f'Response generation took {duration: .2f}s', actor='system'))
