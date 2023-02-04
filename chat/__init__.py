import os

import index

from .base import (
    BaseChat,
    ChatVariant,
)
from .simple import SimpleChat
from .rephrase import RephraseChat
from .rephrase_cited import RephraseCitedChat
from .widget_search import WidgetSearchChat


DEFAULT_CHAT_VARIANT = ChatVariant.widget_search


def new_chat(chat_variant: ChatVariant = DEFAULT_CHAT_VARIANT, show_intermediate_output: bool = True) -> BaseChat:
    docsearch = index.get_docsearch()
    if chat_variant == ChatVariant.simple:
        return SimpleChat(docsearch)
    elif chat_variant == ChatVariant.rephrase:
        return RephraseChat(docsearch, show_rephrased=show_intermediate_output)
    elif chat_variant == ChatVariant.rephrase_cited:
        return RephraseCitedChat(docsearch, show_rephrased=show_intermediate_output)
    elif chat_variant == ChatVariant.widget_search:
        widget_search = index.get_widget_search()
        return WidgetSearchChat(docsearch, widget_search, show_thinking=show_intermediate_output)
    else:
        raise ValueError(f'unrecognized chat variant: {chat_variant}')
