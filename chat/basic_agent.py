# This chat variant uses an agent with access to tools

import os
import time
from typing import Any, Callable, List

import context
import registry
import streaming
from tools.base import BaseTool
from .base import BaseChat, ChatHistory, Response


# We mirror these from langchain/agents/conversational/prompt.py, so we can modify them
PREFIX = """You are a web3 assistant. You help users use web3 apps, such as Uniswap, AAVE, MakerDao, etc. You assist users in achieving their goals with these protocols, by providing users with relevant information, and creating transactions for users. Your responses should sound natural, helpful, cheerful, and engaging, and you should use easy to understand language with explanations for jargon.

TOOLS:
------

You can delegate your response to the user to any of the following tools which may utilize external sources of information, but you must provide it a summary of relevant facts from the chat history so far. If you need more input from the user, don't use a tool but output DONE."""
FORMAT_INSTRUCTIONS = """To use a tool, please use the following format and think step by step:

```
Thought: you should always think about what to do, explicitly restating the task without pronouns and restating details based on the conversation history and new input.
Prior Observations: restate verbatim ALL details/names/figures/facts/etc from past observations relevant to the task and ALL related entities.
Action Reasoning: reasoning about which action/tool would be useful for task given knowledge.
Action: the action/tool to use, should be one of [{tool_names}]
Action Input: the input to the action/tool with the thought/intent and all details of relevant facts from conversation history, matching the tool input format.
Observation: the response to the {human_prefix} from the action.
... (this Thought/Prior Observations/Action Reasoning/Action/Action Input/Observation can repeat N times)
Thought: I have nothing more to say to {human_prefix}, or I need more input from the {human_prefix}, or the {human_prefix} has been shown a widget magic command.
{ai_prefix}: DONE
```
"""

SUFFIX = """Begin!

Previous conversation history:
{chat_history}

New input: {input}
Thought: {agent_scratchpad}"""


@registry.register_class
class BasicAgentChat(BaseChat):
    def __init__(self, tools: List[BaseTool], show_thinking: bool = True) -> None:
        super().__init__()
        self.tools = tools
        self.show_thinking = show_thinking

    def receive_input(self, history: ChatHistory, userinput: str, send: Callable) -> None:
        userinput = userinput.strip()
        history_string = history.to_string(bot_prefix="Observation", system_prefix="Thought")

        history.add_user_message(userinput)
        start = time.time()

        system_chat_message_id = None
        system_response = ''
        bot_chat_message_id = None
        bot_response = ''

        def system_flush(response):
            nonlocal system_chat_message_id
            response = response.strip()
            send(Response(
                response=response,
                still_thinking=True,
                actor='system',
                operation='replace',
            ), last_chat_message_id=system_chat_message_id)
            history.add_system_message(response)

        def bot_flush(response):
            nonlocal bot_chat_message_id
            response = response.strip()
            send(Response(
                response=response,
                still_thinking=False,
                actor='bot',
                operation='replace',
            ), last_chat_message_id=bot_chat_message_id)
            history.add_bot_message(response)

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
            if not bot_response.strip():
                # don't start returning something until we have the first non-whitespace char
                return
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
            verbose=True,
            agent_kwargs=dict(
                ai_prefix="Assistant",
                human_prefix="User",
                prefix=PREFIX,
                suffix=SUFFIX,
                format_instructions=FORMAT_INSTRUCTIONS,
            ),
        )
        example = {
            'input': userinput,
            'chat_history': history_string,
        }
        with context.with_wallet_address(history.wallet_address):
            result = agent.run(example).strip()
        duration = time.time() - start

        if system_chat_message_id is not None:
            system_flush(system_response)

        if bot_chat_message_id is not None:
            bot_flush(result)
        else:
            if result != 'DONE':
                send(Response(response=result))

        send(Response(response=f'Response generation took {duration: .2f}s', actor='system'))
