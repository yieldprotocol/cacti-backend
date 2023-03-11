import sys
import re
import requests
import time
import random

from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.prompts.base import BaseOutputParser

from utils import *
set_api_key()

TEMPLATE = \
'''
Query: {query}
Note: The query is related to the blockchain ecosystem.
Generate 10 related searches most asked on the web. 
1.'''

class ChatOutputParser(BaseOutputParser):

    @property
    def _type(self) -> str:
        """Return the type key."""
        return "chat_output_parser"

    def parse(self, text: str) -> str:
        """Parse the output of an LLM call."""
        text = text.strip()
        text = re.sub(r"\d+. ", '', text)
        text = text.split('\n')
        return text
    

class SearchURLs():
    def __init__(self,) -> None:
        super().__init__()
        llm = OpenAI(
            temperature=1.0, max_tokens=-1,
        )
        output_parser = ChatOutputParser()
        relSearch_prompt = PromptTemplate(
            input_variables=["query"],
            template=TEMPLATE,
            output_parser=output_parser,
        )
        self.chain = LLMChain(llm=llm, prompt=relSearch_prompt, verbose=False)

        subscription_key="c6279a2b2a41436caa61fe104e464404"
        self.search_url = "https://api.bing.microsoft.com/v7.0/search"
        self.headers = {"Ocp-Apim-Subscription-Key" : subscription_key}

        self.all_urls, self.all_queries = set(), set()

    def via_llm(self, query): 
        relSearches = self.chain.apply_and_parse([{"query": query}])[0]
        time.sleep(random.randint(1, 7))
        return relSearches

    def via_bing(self, query):
        query = query+" Note: The query is related to the blockchain ecosystem."
        params  = {"q": query, "textDecorations": True, "textFormat": "HTML"}
        response = requests.get(self.search_url, headers=self.headers, params=params)
        response.raise_for_status()
        response = response.json()
        urls = [x['url'] for x in response['webPages']['value']]
        try: relSearches = [r['text'] for r in response['relatedSearches']['value']]
        except: relSearches = []
        return urls, relSearches
    
    def find_urls(self, query, depth=2):
        urls, relS_bing = self.via_bing(query)
        self.all_urls.update(set(urls))
        relS_llm = self.via_llm(query)
        # if depth==0: return {query: urls}
        if depth==0: return urls
        relS = relS_bing + relS_llm
        q_urls = set()
        for q in relS:
            if q in self.all_queries: continue
            x = self.find_urls(q, depth=depth-1)
            self.all_queries.add(q)
            q_urls.update(set(x))
        return q_urls