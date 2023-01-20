from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class Interaction:
    input: str
    response: str


class BaseChat:
    """Common interface for chat."""

    def __init__(self) -> None:
        """Initialize chat."""
        self.history: List[Interaction] = []

    @abstractmethod
    def chat(self, user_input: str) -> str:
        """Accept user input and return response."""

    def add_interaction(self, user_input: str, response: str) -> None:
        """Add interaction to history."""
        self.history.append(Interaction(input=user_input, response=response))
