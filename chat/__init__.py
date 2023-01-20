import os

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain.llms import OpenAI

from .base import BaseChat
from .simple import SimpleChat


USE_SIMPLE = True


os.environ["OPENAI_API_KEY"] = "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"
OpenAI.api_key = "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"
embeddings = OpenAIEmbeddings()
with open('./web3fuctions.txt') as f:
    web3functions = f.read()
# text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
# instructions = text_splitter.split_text(ladle)
instructions = web3functions.split("---")
print(instructions)
docsearch = FAISS.from_texts(instructions, embeddings)


def new_chat() -> BaseChat:
    if USE_SIMPLE:
        return SimpleChat(docsearch)
