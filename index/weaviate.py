import weaviate  # type: ignore

import utils


def get_client() -> weaviate.Client:
    client = weaviate.Client(
        url=utils.WEAVIATE_URL,
        additional_headers={"X-OpenAI-Api-Key": utils.OPENAI_API_KEY},
    )
    return client
