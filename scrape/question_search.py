import sys
import re
import requests
import time
import random

import praw

from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.prompts.base import BaseOutputParser

from .url_search import *
from utils import *
set_api_key()

BLACKLISTED_TITLES = ['Frequently Asked Questions + Weekly Discussion Thread',
                      'Welcome to r/Coinbase! | Help: help.coinbase.com | As a reminder, our only official Coinbase Support presence on Reddit is u/coinbasesupport.']

SUBREDDITS = set([
'Coinbase',
'MakerDao',
'UniSwap',
'opensea',
'LidoFinance',
'ethereum',
'YugaLabs',
'MyEtherWallet',
'stashinvest',
'CurveFinance',
])

TURN2QUES_TEMPLATE = \
'''
Read the following Reddit posts. For each, please identify the questions the author of the post is trying to have answered, or any questions that a reader of the post who knows nothing about the topic is likely to have. 

Subreddit: r/ethereum
Post title: How find the same/similar smart contract on a tesnet?
Post body: I'm trying to copy an app that's running on the main net. It's using a lot of smart contracts and tokens deployed on the main net. Is there anyway I can find these smart contracts on the goerli test net and not copy and deploy them one by one?
Questions:
How can I find testnet deployments of Ethereum mainnet protocols?
What is the goerli testnet?
How can I deploy an app on a testnet? 
How can I integrate with smart contracts on a testnet?

Subreddit: r/ethereum
Post title: My transaction is stuck for over 2h
Post body: Hi

so I made a transaction on uniswap and its in pending state for over 2h. I can not cancel as 'cancel' button on metamask is not avaliable, I can not speed it up as nothing is happening when I hit speed up button. What are my options?
Questions:
How can I cancel a transaction?
How can I speed up a transaction?
How does canceling a transaction work?
How does "speeding up" a transaction work? 
What can I do about a stuck transaction in metamask? 
What do you do when a transaction is pending for a long time? 

Subreddit: r/CoinBase
Post title: XRP disappeared from wallet. What do I do?
Post body:
Questions:
What happened to my XRP?
Why is my XRP missing from my wallet?
How can I recover my XRP?
What should I do if I can't find my XRP in my wallet? 
What are the possible causes of XRP disappearing from my wallet?

Subreddit: r/{subreddit}
Post title: {title}
Post body: {body}
Questions:'''


class ChatOutputParser(BaseOutputParser):

    @property
    def _type(self) -> str:
        """Return the type key."""
        return "chat_output_parser"

    def parse(self, text: str) -> str:
        """Parse the output of an LLM call."""
        text = text.strip()
        text = text.split('\n')
        return text


class QueryOnReddit():
    def __init__(self,) -> None:
        super().__init__()
        llm = OpenAI(
            temperature=0.8, max_tokens=-1,
        )
        output_parser = ChatOutputParser()
        turn2ques_prompt = PromptTemplate(
            input_variables=["subreddit", "body", "title"],
            template=TURN2QUES_TEMPLATE,
            output_parser=output_parser,
        )
        self.chain = LLMChain(llm=llm, prompt=turn2ques_prompt, verbose=False)
        self.reddit = praw.Reddit(client_id='vNryBhGWEDDKjF1KiRabfQ', client_secret='VgPhCqfZ707LimGMu4FzAHNSfFdQhw', user_agent='crypto_data')
        self.searcher = SearchURLs()

    def get_queries(self, subreddit, limit=200): 
        hot_posts = self.reddit.subreddit(subreddit).hot(limit=limit)
        for post in hot_posts:
            title = post.title
            if title in BLACKLISTED_TITLES: continue
            if title.endswith('?') and len(title.split())>5:
                query = max(self.chain.apply_and_parse([{"subreddit": subreddit, "title": title, "body": post.selftext}])[0], key=len)
                urls = self.searcher.find_urls(query)
                yield urls
                time.sleep(random.randint(1, 7))
        