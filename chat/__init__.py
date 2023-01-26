import os

import index

from .base import (
    BaseChat,
    ChatVariant,
)
from .simple import SimpleChat
from .rephrase import RephraseChat


def new_chat(chat_variant: ChatVariant = ChatVariant.rephrase, show_intermediate_output: bool = True) -> BaseChat:
    docsearch = index.get_docsearch()
    if chat_variant == ChatVariant.simple:
        return SimpleChat(docsearch)
    elif chat_variant == ChatVariant.rephrase:
        return RephraseChat(docsearch, show_rephrased=show_intermediate_output)
    else:
        raise ValueError(f'unrecognized chat variant: {chat_variant}')
