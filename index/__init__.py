from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain.llms import OpenAI
from langchain.text_splitter import CharacterTextSplitter


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
