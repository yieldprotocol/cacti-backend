from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Any, Callable, Dict, List, Optional, Union
import uuid

from langchain.schema import AgentAction, AgentFinish, LLMResult
from langchain.prompts.base import BaseOutputParser


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
    def receive_input(self, history: ChatHistory, user_input: str, send_message: Callable) -> None:
        """Accept user input and return responses via the send_message function."""


class ChatOutputParser(BaseOutputParser):

    @property
    def _type(self) -> str:
        """Return the type key."""
        return "chat_output_parser"

    def parse(self, text: str) -> str:
        """Parse the output of an LLM call."""
        ret = text.strip()
        return ret
