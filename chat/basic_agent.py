# This chat variant uses an agent with access to tools

import os
import time
from typing import Any, Callable, List

import registry
import streaming
from tools.base import BaseTool
from .base import BaseChat, ChatHistory, Response


# We mirror these from langchain/agents/conversational/prompt.py, so we can modify them
PREFIX = """You are a web3 assistant. You help users use web3 apps, such as Uniswap, AAVE, MakerDao, etc. You assist users in achieving their goals with these protocols, by providing users with relevant information, and creating transactions for users. Your responses should sound natural, helpful, cheerful, and engaging, and you should use easy to understand language with explanations for jargon.

TOOLS:
------

You have access to the following tools:"""
FORMAT_INSTRUCTIONS = """To use a tool, please use the following format:

```
Thought: Do I need to use a tool? Yes.
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action.
Observation: the result of the action.
```

If the last observation is useful as your response, you do not have to repeat it, you may just respond with "DONE".
When you have a response to say to the {human_prefix}, or if you do not need to use a tool, you MUST use the format:

```
Thought: Do I need to use a tool? No.
{ai_prefix}: [your response here].
```

"""

SUFFIX = """Begin!

Previous conversation history:
{chat_history}

New input: {input}
{agent_scratchpad}"""


@registry.register_class
class BasicAgentChat(BaseChat):
    def __init__(self, tools: List[BaseTool], show_thinking: bool = True) -> None:
        super().__init__()
        self.tools = tools
        self.show_thinking = show_thinking

    def receive_input(self, history: ChatHistory, userinput: str, send: Callable) -> None:
        userinput = userinput.strip()
        history_string = ""
        for interaction in history:
            history_string += ("User: " + interaction.input + "\n")
            history_string += ("Assistant: " + interaction.response + "\n")
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
        result = agent.run(example).strip()
        duration = time.time() - start
        history.add_interaction(userinput, result)

        if system_chat_message_id is not None:
            system_flush(system_response)

        if bot_chat_message_id is not None:
            bot_flush(result)
        else:
            if result != 'DONE':
                send(Response(response=result))

        send(Response(response=f'Response generation took {duration: .2f}s', actor='system'))
