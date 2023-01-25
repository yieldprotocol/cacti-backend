import os

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain.llms import OpenAI
from langchain.text_splitter import CharacterTextSplitter

from .base import (
    BaseChat,
    ChatVariant,
)
from .simple import SimpleChat
from .rephrase import RephraseChat
from utils import set_api_key


set_api_key()


_docsearch = None

def get_docsearch():
    global _docsearch
    if _docsearch is None:
        embeddings = OpenAIEmbeddings()
        with open('./web3fuctions.txt') as f:
            web3functions = f.read()
        # text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        # instructions = text_splitter.split_text(ladle)
        documents = web3functions.split("---")
        #print(documents)
        _docsearch = FAISS.from_texts(documents, embeddings)
    return _docsearch


def new_chat(chat_variant: ChatVariant = ChatVariant.rephrase, show_intermediate_output: bool = True) -> BaseChat:
    docsearch = get_docsearch()
    if chat_variant == ChatVariant.simple:
        return SimpleChat(docsearch)
    elif chat_variant == ChatVariant.rephrase:
        return RephraseChat(docsearch, show_rephrased=show_intermediate_output)
    else:
        raise ValueError(f'unrecognized chat variant: {chat_variant}')
