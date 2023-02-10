import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import List, Generator


class ChatVariant(enum.IntEnum):
    simple = 1
    rephrase = 2
    rephrase_cited = 3
    widget_search = 4


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


class BaseChat:
    """Common interface for chat."""

    def __init__(self) -> None:
        """Initialize chat."""
        self.history: List[Interaction] = []

    @abstractmethod
    def chat(self, user_input: str) -> Generator[Response, None, None]:
        """Accept user input and return response."""

    def add_interaction(self, user_input: str, response: str) -> None:
        """Add interaction to history."""
        self.history.append(Interaction(input=user_input, response=response))
