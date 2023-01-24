from dataclasses import dataclass
from dataclasses_json import dataclass_json

from chat.base import Interaction


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
