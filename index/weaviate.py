from typing import Optional, List

import weaviate  # type: ignore
from langchain.vectorstores import Weaviate

import utils
import registry


def get_client() -> weaviate.Client:
    client = weaviate.Client(
        url=utils.WEAVIATE_URL,
        additional_headers={"X-OpenAI-Api-Key": utils.OPENAI_API_KEY},
    )
    return client


@registry.register_class
class WeaviateIndex(Weaviate):
    """Thin wrapper around langchain's vector store."""
    def __init__(self, index_name: str, text_key: str, extra_keys: Optional[List[str]] = None) -> None:
        client = get_client()
        super().__init__(client, index_name, text_key, extra_keys or [])
