from typing import Any, Iterable, List, Optional
import os
import traceback

from langchain.docstore.document import Document
from .weaviate import get_client


INDEX_NAME = 'AppInfoV1'
INDEX_DESCRIPTION = "Index of app info"
QUESTION_KEY = 'question'
ANSWER_KEY = 'answer'
FOLLOW_UPS_KEY = 'suggested_follow_ups'


KEY_TO_PREFIX = {
    QUESTION_KEY: 'Question: ',
    ANSWER_KEY: 'Answer: ',
    FOLLOW_UPS_KEY: 'Suggested follow ups: ',
}


def delete_schema() -> None:
    client = get_client()
    client.schema.delete_class(INDEX_NAME)


def create_schema(delete_first: bool = False) -> None:
    client = get_client()
    
    # TODO: if schema exists delete
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
                        "description": "Question about the app",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,
                                "vectorizePropertyName": True,
                            }
                        },
                        "name": QUESTION_KEY,
                    },
                    {
                        "dataType": ["text"],
                        "description": "Answer to question about the app",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,
                                "vectorizePropertyName": True,
                            }
                        },
                        "name": ANSWER_KEY,
                    },
                    {
                        "dataType": ["text"],
                        "description": "Suggested follow ups",
                        "name": FOLLOW_UPS_KEY,
                    },
                ],
            },
        ]
    }
    client.schema.create(schema)


# run with: python3 -c "from index import app_info; app_info.backfill()"
def backfill():
    # TODO: right now we don't have stable document IDs unlike sites.
    # Always drop and recreate first.
    create_schema(delete_first=False)

    from langchain.vectorstores import Weaviate
    with open('./knowledge_base/app_info.txt') as f:
        data = f.read()
    metadatas = list(map(_parse_document, data.split("---")))
    documents = [d.pop(QUESTION_KEY) for d in metadatas]

    client = get_client()
    w = Weaviate(client, INDEX_NAME, QUESTION_KEY)
    w.add_texts(documents, metadatas)


def _parse_document(doc_lines):
    doc = {}
    for line in doc_lines.strip().split('\n'):
        for key, prefix in KEY_TO_PREFIX.items():
            if line.startswith(prefix):
                doc[key] = line[len(prefix):]
                break
    assert len(doc) == len(KEY_TO_PREFIX)
    return doc
