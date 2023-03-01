from typing import Any, Iterable, List, Optional
import os
import traceback
import json

from langchain.docstore.document import Document
from .weaviate import get_client


INDEX_NAME = 'CryptoTokensV1'
INDEX_DESCRIPTION = "Index of Crypto Tokens"
CANONICAL_ID_KEY = 'canonical_id'
SYMBOL_KEY = "symbol"
NAME_KEY = "name"



def delete_schema() -> None:
    client = get_client()
    client.schema.delete_class(INDEX_NAME)


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
                        "description": "The canonical ID of the crypto token",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,
                                "vectorizePropertyName": False,
                            }
                        },
                        "name": CANONICAL_ID_KEY,
                    },
                    {
                        "dataType": ["text"],
                        "description": "The name of the crypto token",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,
                                "vectorizePropertyName": False,
                            }
                        },
                        "name": NAME_KEY,
                    },
                    {
                        "dataType": ["text"],
                        "description": "The symbol of the crypto token",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,
                                "vectorizePropertyName": False,
                            }
                        },
                        "name": SYMBOL_KEY,
                    },
                ],
            },
        ]
    }
    client.schema.create(schema)


# run with: python3 -c "from index import crypto_tokens; crypto_tokens.backfill()"
def backfill():
    # TODO: right now we don't have stable document IDs unlike sites.
    # Always drop and recreate first.
    create_schema(delete_first=True)

    from langchain.vectorstores import Weaviate

    
    with open('./knowledge_base/crypto_tokens.json') as f:
        crypto_tokens = json.load(f)
        documents = [c.pop("id") for c in crypto_tokens]

    client = get_client()
    w = Weaviate(client, INDEX_NAME, CANONICAL_ID_KEY)
    w.add_texts(documents, crypto_tokens)