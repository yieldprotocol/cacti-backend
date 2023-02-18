from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Any, Callable, Dict, List, Generator, Optional, Union
import uuid

from langchain.callbacks.base import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult


@dataclass_json
@dataclass
class Interaction:
    input: str
    response: str


@dataclass_json
@dataclass
class Response:
    response: str
    actor: str = 'bot'
    still_thinking: bool = False
    operation: str = 'create'


@dataclass
class ChatHistory:
    interactions: List[Interaction]
    session_id: Optional[uuid.UUID]

    def add_interaction(self, user_input: str, response: str) -> None:
        """Add interaction to history."""
        self.interactions.append(Interaction(input=user_input, response=response))

    def __bool__(self):
        return bool(self.interactions)

    def __iter__(self):
        return iter(self.interactions)

    @classmethod
    def new(cls, session_id: Optional[uuid.UUID] = None):
        return cls(interactions=[], session_id=session_id)



class BaseChat(ABC):
    """Common interface for chat."""

    @abstractmethod
    def receive_input(self, history: ChatHistory, user_input: str, send_message: Callable) -> Generator[Response, None, None]:
        """Accept user input and return response."""


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
