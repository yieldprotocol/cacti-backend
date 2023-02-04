from typing import Any, Iterable, List, Optional
import os
import traceback
import uuid

from langchain.docstore.document import Document
from .weaviate import get_client


# set an arbitrary uuid for namespace, for consistent uuids for objects
NAMESPACE_UUID = uuid.UUID('64265e01-0339-4063-8aa3-bcd562b55aea')
INDEX_NAME = 'WidgetV1'
INDEX_DESCRIPTION = "Index of widgets"
TEXT_KEY = 'content'


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
                "description": INDEX_DESCRIPTION,
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
                ],
            },
        ]
    }
    client.schema.create(schema)


# run with: python3 -c "from index import widgets; widgets.backfill()"
def backfill():
    # TODO: right now we don't have stable document IDs unlike sites.
    # Always drop and recreate first.
    create_schema(delete_first=True)

    from langchain.vectorstores import Weaviate
    with open('./web3fuctions.txt') as f:
        web3functions = f.read()
    documents = web3functions.split("---")
    metadatas = [{} for _ in documents]

    client = get_client()
    w = Weaviate(client, INDEX_NAME, TEXT_KEY)
    w.add_texts(documents, metadatas)