from typing import Any, Dict, List, Optional

from langchain.chains.api.base import APIChain as LangChainAPIChain
from langchain.llms.base import BaseLLM
from langchain.requests import RequestsWrapper
from langchain.prompts.prompt import PromptTemplate

import registry


# original version at langchain/chains/api/prompt.py
API_URL_PROMPT_TEMPLATE = """You are given the below API Documentation:
{api_docs}
Using this documentation, generate the full API url to call for answering the user question.
You should build the API url in order to get a response that is as short as possible, while still getting the necessary information to answer the question. Pay attention to deliberately exclude any unnecessary pieces of data in the API call.

Question:{question}
API url:"""

API_URL_PROMPT = PromptTemplate(
    input_variables=[
        "api_docs",
        "question",
    ],
    template=API_URL_PROMPT_TEMPLATE,
)

API_RESPONSE_PROMPT_TEMPLATE = (
    API_URL_PROMPT_TEMPLATE
    + """ {api_url}

Here is the response from the API:

{api_response}

Summarize this response to answer the original question.

Summary:"""
)

API_RESPONSE_PROMPT = PromptTemplate(
    input_variables=["api_docs", "question", "api_url", "api_response"],
    template=API_RESPONSE_PROMPT_TEMPLATE,
)


@registry.register_class
class IndexAPIChain(LangChainAPIChain):
    api_docs_key: str = "api_docs"
    headers_key: str = "headers"

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        """Override the base function to reset instance variables to use relevant input values at query time"""

        api_docs = inputs[self.api_docs_key]
        headers = inputs.get(self.headers_key, None)

        self.api_docs = api_docs
        self.requests_wrapper = RequestsWrapper(headers=headers)
        return super()._call(inputs)

    @classmethod
    def from_llm(
        cls,
        llm: BaseLLM,
        **kwargs: Any,
    ) -> LangChainAPIChain:
        return super().from_llm_and_api_docs(
            llm=llm,
            api_docs="",
            api_url_prompt=API_URL_PROMPT,
            api_response_prompt=API_RESPONSE_PROMPT,
            **kwargs
        )
