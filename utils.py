import os

from langchain.llms import OpenAI


API_KEY = "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"


def set_api_key():
    os.environ["OPENAI_API_KEY"] = API_KEY
    OpenAI.api_key = API_KEY
