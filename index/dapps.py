# to build the index for dapps, first scrape them using the scraper
# then run: python3 -c "from index.dapps import backfill; backfill()"


from langchain.docstore.document import Document
from .weaviate import get_client
import json

INDEX_NAME = "Web3Apps"
INDEX_DESCRIPTION = "Index of Third party dapps"
DAPP_DESCRIPTION = "description"
DAPP_NAME = "name"
DAPP_URL = "url"

def delete_schema() -> None:
    try: 
        client = get_client()
        client.schema.delete_class(INDEX_NAME)
    except Exception as e: 
        print(f"Error deleting schmea: {str(e)}")

def create_schema(delete_first: bool = False) -> None:
    try: 
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
                            "type": "text"
                        }
                    },
                    "properties": [
                        {"name": DAPP_NAME, "dataType": ["text"]},
                        {"name": DAPP_DESCRIPTION, "dataType": ["text"]},
                        {"name": DAPP_URL, "dataType": ["text"]},
                        {
                            "name": "twitterHandle",
                            "dataType": ["text"],
                            "description": "The Twitter handle of the Dapp",
                            "moduleConfig": {
                                    "text2vec-openai": {
                                    "skip": True,
                                    "vectorizePropertyName": False
                                }
                            }
                        },
                        {
                            "name": "blogLinks",
                            "dataType": ["text[]"],
                            "description": "Links to the blog posts related to the Dapp",
                            "moduleConfig": {
                                    "text2vec-openai": {
                                    "skip": True,
                                    "vectorizePropertyName": False
                                }
                            }
                        },
                        {
                            "name": "discord",
                            "dataType": ["text"],
                            "description": "The Discord server link of the Dapp",
                            "moduleConfig": {
                                    "text2vec-openai": {
                                    "skip": True,
                                    "vectorizePropertyName": False
                                }
                            }
                        },
                        {
                            "name": "facebook",
                            "dataType": ["text"],
                            "description": "The Facebook page link of the Dapp",
                            "moduleConfig": {
                                    "text2vec-openai": {
                                    "skip": True,
                                    "vectorizePropertyName": False
                                }
                            }
                        },
                        {
                            "name": "instagram",
                            "dataType": ["text"],
                            "description": "The Instagram profile link of the Dapp",
                            "moduleConfig": {
                                    "text2vec-openai": {
                                    "skip": True,
                                    "vectorizePropertyName": False
                                }
                            }
                        },
                        {
                            "name": "telegram",
                            "dataType": ["text"],
                            "description": "The Telegram channel link of the Dapp",
                            "moduleConfig": {
                                    "text2vec-openai": {
                                    "skip": True,
                                    "vectorizePropertyName": False
                                }
                            }
                        }
                    ]
                }
        
            ]
        }
        client.schema.create(schema)
    except Exception as e:
        print(f"Error creating schema: {str(e)}")

def backfill():
    try: 
        from langchain.vectorstores import Weaviate

        with open('./knowledge_base/dapps_ranked.json') as f: 
            dapp_list = json.load(f)
            
        # Extract the 'name' field from each dapp and store it in the 'documents' list
        documents = [d.pop("name") for d in dapp_list]

        # Use the remaining fields in each dapp to populate the 'metadatas' list
        # is this the best 'metadatas' to use?
        metadatas = dapp_list
            
        create_schema(delete_first=True)

        client = get_client()
        w = Weaviate(client, INDEX_NAME, DAPP_NAME) # is this a proper 3rd argument?
        w.add_texts(documents, metadatas)
    except Exception as e: 
        print(f"Error during backfill in dapps.py {str(e)}")


