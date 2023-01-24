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


os.environ["OPENAI_API_KEY"] = "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"
OpenAI.api_key = "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"


_docsearch = None

def get_docsearch():
    global _docsearch
    if _docsearch is None:
        embeddings = OpenAIEmbeddings()
        '''
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        SCRAPE_DIR = '../../deep-cookie/protocols-scraped_data/lido-documentation'
        scrape_dir = os.path.join(os.path.dirname(__file__), SCRAPE_DIR)
        documents = []
        for filename in os.listdir(scrape_dir):
            filepath = os.path.join(scrape_dir, filename)
            lines = list(open(filepath).readlines())
            content = '\n'.join(lines)
            docs = text_splitter.split_text(content)
            documents.extend(docs)

        '''
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
