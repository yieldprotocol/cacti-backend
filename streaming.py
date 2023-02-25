from typing import Any, Callable

from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.agents import initialize_agent
from langchain.callbacks.base import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

import config


class StreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """Override the minimal handler to get the token."""

    def __init__(self, new_token_handler: Callable) -> None:
        self.new_token_handler = new_token_handler

    @property
    def always_verbose(self) -> bool:
        return True

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""
        self.new_token_handler(token)


def streaming_callback_manager(new_token_handler: Callable) -> CallbackManager:
    return CallbackManager([StreamingCallbackHandler(new_token_handler)])


def get_streaming_llm(new_token_handler):
    # falls back to non-streaming if none provided
    streaming_kwargs = dict(
        streaming=True,
        callback_manager=streaming_callback_manager(new_token_handler),
    ) if new_token_handler else {}

    llm = OpenAI(
        temperature=0.0, max_tokens=-1,
        **streaming_kwargs
    )
    return llm


def get_streaming_chain(prompt, new_token_handler):
    llm = get_streaming_llm(new_token_handler)
    chain = LLMChain(llm=llm, prompt=prompt, verbose=True)
    return chain


def get_streaming_tools(tools, new_token_handler):
    streaming_tools = config.initialize_streaming(tools, new_token_handler)
    return streaming_tools


def get_streaming_agent(tools, new_token_handler, **agent_kwargs):
    llm = get_streaming_llm(new_token_handler)
    agent = initialize_agent(tools, llm, agent="conversational-react-description", **agent_kwargs)
    return agent
