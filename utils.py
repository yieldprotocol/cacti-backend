import os

from langchain.llms import OpenAI


OPENAI_API_KEY = "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"
WEAVIATE_URL = "http://0.0.0.0:8080"



def set_api_key():
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    OpenAI.api_key = OPENAI_API_KEY
