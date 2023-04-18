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

    def add_user_message(self, text: str, message_id: Optional[uuid.UUID] = None, before_message_id: Optional[uuid.UUID] = None) -> None:
        """Add user message to history."""
        self._add_message(text, 'user', message_id=message_id, before_message_id=before_message_id)

    def add_bot_message(self, text: str, message_id: Optional[uuid.UUID] = None, before_message_id: Optional[uuid.UUID] = None) -> None:
        """Add bot message to history."""
        text = parse_widgets_into_text(text)
        self._add_message(text, 'bot', message_id=message_id, before_message_id=before_message_id)

    def add_system_message(self, text: str, message_id: Optional[uuid.UUID] = None, before_message_id: Optional[uuid.UUID] = None) -> None:
        """Add system message to history."""
        self._add_message(text, 'system', message_id=message_id, before_message_id=before_message_id)

    def _add_message(self, text: str, actor: str, message_id: Optional[uuid.UUID] = None, before_message_id: Optional[uuid.UUID] = None) -> None:
        """Add message to history with given message id if specified, before message id if specified."""
        insert_idx = None
        if before_message_id is not None:
            for idx in range(len(self.messages)):
                if self.messages[idx].message_id == before_message_id:
                    insert_idx = idx
                    break
        chat_message = ChatMessage(actor=actor, content=text, message_id=message_id)
        if insert_idx is not None:
            self.messages.insert(insert_idx, chat_message)
        else:
            self.messages.append(chat_message)

    def find_next_user_message(self, message_id: uuid.UUID) -> Optional[uuid.UUID]:
        """Find the ID of the next user message after the specified one, if any."""
        next_user_message_id = None
        for idx in range(len(self.messages)):
            if self.messages[idx].message_id == message_id:
                for idx2 in range(idx + 1, len(self.messages)):
                    if self.messages[idx2].actor == 'user':
                        next_user_message_id = self.messages[idx2].message_id
                        break
                break
        return next_user_message_id

    def truncate_from_message(self, message_id: uuid.UUID, before_message_id: Optional[uuid.UUID] = None) -> List[uuid.UUID]:
        """Truncate history from given message id onwards, up to a certain message id if specified.

        Returns list of removed IDs.

        """
        start_idx = None
        end_idx = None
        for idx in range(len(self.messages)):
            if self.messages[idx].message_id == message_id:
                start_idx = idx
                if before_message_id:
                    for idx2 in range(idx + 1, len(self.messages)):
                        if self.messages[idx2].message_id == before_message_id:
                            end_idx = idx2
                            break
                break
        if start_idx is not None:
            removed_ids = [msg.message_id for msg in self.messages[start_idx:end_idx]]
            self.messages[start_idx:end_idx] = []
            return removed_ids
        return []

    def __bool__(self):
        return bool(self.messages)

    def __iter__(self):
        return iter(self.messages)

    def to_string(self, user_prefix: str = "User", bot_prefix: str = "Assistant", system_prefix: str = "System", token_limit: Optional[int] = None, before_message_id : Optional[uuid.UUID] = None) -> str:
        ret = []
        for message in self:
            if before_message_id is not None and message.message_id == before_message_id:
                break
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
    def receive_input(self, history: ChatHistory, user_input: str, send_message: Callable, message_id: Optional[uuid.UUID], before_message_id: Optional[uuid.UUID]) -> None:
        """Accept user input and return responses via the send_message function.

        If message_id is specified, this references the user message id and we add that to history.
        If before_message_id is specified, we insert any new messages before that id.

        """


class ChatOutputParser(BaseOutputParser):

    @property
    def _type(self) -> str:
        """Return the type key."""
        return "chat_output_parser"

    def parse(self, text: str) -> str:
        """Parse the output of an LLM call."""
        ret = text.strip()
        return ret
