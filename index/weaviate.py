from typing import List
import os
import traceback
import uuid

import weaviate  # type: ignore
from langchain.docstore.document import Document
#from langchain.text_splitter import CharacterTextSplitter
from .text_splitter import TokenTextSplitter

import utils


# set an arbitrary uuid for namespace, for consistent uuids for objects
namespace_uuid = uuid.UUID('64265e01-0339-4063-8aa3-bcd562b55aea')
INDEX_NAME = 'IndexV1'
TEXT_KEY = 'content'
SOURCE_URL_KEY = 'url'


#text_splitter = CharacterTextSplitter(
#    chunk_size=1000,
#    chunk_overlap=200,
#)
text_splitter = TokenTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)


def get_client() -> weaviate.Client:
    client = weaviate.Client(
        url=utils.WEAVIATE_URL,
        additional_headers={"X-OpenAI-Api-Key": utils.OPENAI_API_KEY},
    )
    return client


def delete_schema() -> None:
    client = get_client()
    client.schema.delete_class(INDEX_NAME)


# recreate schema with:
# python3 -c "from index import weaviate; weaviate.create_schema(delete_first=True)"

def create_schema(delete_first: bool = False) -> None:
    client = get_client()
    if delete_first:
        delete_schema()
    client.schema.get()
    schema = {
        "classes": [
            {
                "class": INDEX_NAME,
                "description": "Index of web3 document chunks",
                "vectorizer": "text2vec-openai",
                "moduleConfig": {
                    "text2vec-openai": {
                        "model": "ada",
                        "modelVersion": "002",
                        "type": "text",
                    }
                },
                "properties": [
                    {
                        "dataType": ["text"],
                        "description": "The content of the chunk",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,
                                "vectorizePropertyName": False,
                            }
                        },
                        "name": TEXT_KEY,
                    },
                    {
                        "dataType": ["text"],
                        "description": "The source url of the chunk",
                        "name": SOURCE_URL_KEY,
                    },
                ],
            },
        ]
    }
    client.schema.create(schema)


# run with: python3 -c "from index import weaviate; weaviate.BACKFILL_txt()"
def BACKFILL_txt():
    from langchain.vectorstores import Weaviate
    with open('./web3fuctions.txt') as f:
        web3functions = f.read()
    documents = web3functions.split("---")
    metadatas = [{SOURCE_URL_KEY: './web3fuctions.txt'} for _ in documents]

    client = get_client()
    w = Weaviate(client, INDEX_NAME, TEXT_KEY)
    w.add_texts(documents, metadatas)


# run with: python3 -c "from index import weaviate; weaviate.BACKFILL_scrape()"
def BACKFILL_scrape():
    from langchain.vectorstores import Weaviate
    from scrape.scrape import get_body_text
    from scrape.models import ScrapedUrl as ScrapedUrlModel

    client = get_client()
    w = Weaviate(client, INDEX_NAME, TEXT_KEY)

    documents = []
    metadatas = []
    for scraped_url in ScrapedUrlModel.query.all():
        print('including for indexing', scraped_url.url)
        output = scraped_url.data
        text = get_body_text(output)
        documents.append(text)
        metadatas.append({SOURCE_URL_KEY: scraped_url.url})
    splitted_docs = text_splitter.create_documents(documents, metadatas=metadatas)
    splitted_texts = [d.page_content for d in splitted_docs]
    splitted_metadatas = [d.metadata for d in splitted_docs]

    w.add_texts(splitted_texts, splitted_metadatas)
