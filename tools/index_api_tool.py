from typing import Any, Optional

from pydantic import Extra
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

import registry
import streaming
import json
from .base import BaseTool

from .index_lookup import IndexLookupTool
from index.weaviate import WeaviateIndex


CONTENT_DESCRIPTION = "This tool is useful when you need to get current data for a given user query. This user query could be related to live prices, news, DeFi, NFTs and other Web3 information. Do not use any other tool if this tool is used"

INPUT_DESCRIPTION = "the entire user query with all revelant contextual information"

OUTPUT_DESCRIPTION = "an API spec for an endpoint that can be used to get the data for the user query"

@registry.register_class
class IndexAPITool(IndexLookupTool):

    crypto_tokens_index: WeaviateIndex
    _chain: LLMChain

    def __init__(
            self,
            *args,
            **kwargs
    ) -> None:

        new_token_handler = kwargs.get('new_token_handler')
        chain = streaming.get_streaming_api_chain(new_token_handler)
        super().__init__(
            *args,
            _chain=chain,
            content_description=CONTENT_DESCRIPTION,
            input_description=INPUT_DESCRIPTION,
            output_description=OUTPUT_DESCRIPTION,
            **kwargs
        )

    def _run(self, query: str) -> str:
        api_docs = super()._run(query)

        if '__price_context_data__' in api_docs:
            docs = self.crypto_tokens_index.similarity_search(query, k=2)
            context_data = self._build_price_context_data(docs)
            api_docs = api_docs.format(__price_context_data__=context_data)

        result = self._chain.run(question=query, api_docs=api_docs)

        return result

    def _build_price_context_data(self, docs):
        context_data = ""
        context_data = '\n'.join([json.dumps({
            "id": doc.page_content,
            "symbol": doc.metadata["symbol"],
            "name": doc.metadata["name"]
        }) for doc in docs])
        return context_data

    async def _arun(self, query: str) -> str:
        raise NotImplementedError(f"{self.__class__.__name__} does not support async")
