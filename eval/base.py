from typing import List
from dataclasses import dataclass
from dataclasses_json import dataclass_json

from chat.base import Interaction, ChatVariant


@dataclass_json
@dataclass
class ScrapedFile:
    filename: str
    content: str


@dataclass_json
@dataclass
class QuestionAnswerChatExample:
    scraped_filename: str
    context: str
    interactions: List[Interaction]


@dataclass_json
@dataclass
class QuestionAnswerChatPrediction:
    chat_variant: ChatVariant
    example: QuestionAnswerChatExample
    responses: List[str]
