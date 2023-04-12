from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Any, Callable, Dict, List, Optional, Union
import uuid

from langchain.schema import AgentAction, AgentFinish, LLMResult
from langchain.prompts.base import BaseOutputParser

import utils
from .display_widgets import parse_widgets_into_text


@dataclass_json
@dataclass
class Response:
    response: str
    actor: str = 'bot'
    still_thinking: bool = False
    operation: str = 'create'


@dataclass
class ChatMessage:
    actor: str
    content: str
    message_id: Optional[uuid.UUID]


@dataclass
class ChatHistory:
    messages: List[ChatMessage]
    session_id: uuid.UUID
    wallet_address: Optional[str]

    def add_interaction(self, user_input: str, response: str) -> None:
        """Add interaction to history."""
        self.add_user_message(user_input)
        self.add_bot_message(response)

    def add_user_message(self, text: str, message_id: Optional[uuid.UUID] = None) -> None:
        """Add user message to history."""
        self.messages.append(ChatMessage(actor='user', content=text, message_id=message_id))

    def add_bot_message(self, text: str, message_id: Optional[uuid.UUID] = None) -> None:
        """Add bot message to history."""
        text = parse_widgets_into_text(text)
        self.messages.append(ChatMessage(actor='bot', content=text, message_id=message_id))

    def add_system_message(self, text: str, message_id: Optional[uuid.UUID] = None) -> None:
        """Add system message to history."""
        self.messages.append(ChatMessage(actor='system', content=text, message_id=message_id))

    def truncate_from_message(self, message_id: uuid.UUID) -> List[uuid.UUID]:
        """Truncate history from given message id onwards. Returns list of removed IDs."""
        for idx in range(len(self.messages)):
            if self.messages[idx].message_id == message_id:
                removed_ids = [msg.message_id for msg in self.messages[idx:]]
                self.messages = self.messages[:idx]
                return removed_ids
        return []

    def __bool__(self):
        return bool(self.messages)

    def __iter__(self):
        return iter(self.messages)

    def to_string(self, user_prefix: str = "User", bot_prefix: str = "Assistant", system_prefix: str = "System", token_limit: Optional[int] = None) -> str:
        ret = []
        for message in self:
            if message.actor == 'user':
                prefix = user_prefix
            elif message.actor == 'system':
                prefix = system_prefix
            else:
                prefix = bot_prefix
            ret.append(f"{prefix}: {message.content}")
        if token_limit is not None:
            total_count = 0
            for idx in reversed(range(len(ret))):
                count = utils.get_token_len(ret[idx])
                if total_count + count > token_limit:
                    ret = ret[idx + 1:]
                    break
                total_count += count
        return "\n".join(ret)

    @classmethod
    def new(cls, session_id: uuid.UUID, wallet_address: Optional[str] = None):
        return cls(messages=[], session_id=session_id, wallet_address=wallet_address)



class BaseChat(ABC):
    """Common interface for chat."""

    @abstractmethod
    def receive_input(self, history: ChatHistory, user_input: str, send_message: Callable, message_id: Optional[uuid.UUID]) -> None:
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
