import os

from langchain.llms import OpenAI


OPENAI_API_KEY = "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"
WEAVIATE_URL = "http://chatweb3:q0jficzXOA69T5FWgAeT@23.20.190.128:5050"



def set_api_key():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    OpenAI.api_key = OPENAI_API_KEY
