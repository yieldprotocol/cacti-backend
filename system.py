import registry
from chat import BaseChat


@registry.register_class
class System:
    def __init__(self, chat: BaseChat) -> None:
        self.chat = chat
