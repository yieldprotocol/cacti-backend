from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS, Weaviate
from langchain.llms import OpenAI
from langchain.text_splitter import CharacterTextSplitter

from .base import (
    IndexVariant,
)


_docsearch = None


def get_docsearch(index_variant: IndexVariant = IndexVariant.weaviate):
    global _docsearch
    if _docsearch is not None:
        return _docsearch

    if index_variant == IndexVariant.faiss:
        embeddings = OpenAIEmbeddings()
        with open('./web3fuctions.txt') as f:
            web3functions = f.read()
        # text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        # instructions = text_splitter.split_text(ladle)
        documents = web3functions.split("---")
        #print(documents)
        _docsearch = FAISS.from_texts(documents, embeddings)

    elif index_variant == IndexVariant.weaviate:
        from index import weaviate, sites
        client = weaviate.get_client()
        _docsearch = Weaviate(client, sites.INDEX_NAME, sites.TEXT_KEY, [sites.SOURCE_URL_KEY])

    else:
        raise ValueError(f'unrecognized chat variant: {chat_variant}')

    return _docsearch


def get_widget_search():
    from index import weaviate, widgets
    client = weaviate.get_client()
    return Weaviate(client, widgets.INDEX_NAME, widgets.TEXT_KEY)
