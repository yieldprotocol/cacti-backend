from typing import Any, Callable

from text_generation import Client
from langchain.llms import OpenAI, HuggingFaceTextGenInference
from langchain.chains import LLMChain
from langchain.agents import initialize_agent
from langchain.callbacks.base import BaseCallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

import config
from agents.conversational import CUSTOM_AGENT_NAME
from chains import IndexAPIChain
from utils.constants import HUGGINGFACE_API_KEY, HUGGINGFACE_INFERENCE_ENDPOINT

import runpod
import os
RPD_GPU = 1 # 1 for 7B
RPD_VOL = 75 #225 GB volume 
RPD_DISK = 25 # 75 disk space
RPD_MODEL_NAME = "tiiuae/falcon-7b-instruct"
RPD_GPU_ID = "NVIDIA A100 80GB PCIe"

class StreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """Override the minimal handler to get the token."""

    def __init__(self, new_token_handler: Callable) -> None:
        self.new_token_handler = new_token_handler

    @property
    def always_verbose(self) -> bool:
        return True

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""
        self.new_token_handler(token)


def create_runpod():
    # this is one-time declaration, start when the server starts, and return the pod object to the calling stream once done
    pod = runpod.create_pod(
            name="Falcon Small Test Streaming",
            image_name="ghcr.io/huggingface/text-generation-inference:0.8.2",
            gpu_type_id= RPD_GPU_ID,
            cloud_type="SECURE",
            docker_args=f"--model-id {RPD_MODEL_NAME} --num-shard {RPD_GPU}",
            gpu_count=RPD_GPU,
            volume_in_gb=RPD_VOL,
            container_disk_in_gb=RPD_DISK,
            ports="80/http",
            volume_mount_path="/data",
        )
    print("created runpod!")
    return pod

def get_streaming_llm(new_token_handler, model_name=None, max_tokens=-1):
    
    if model_name=='huggingface-llm':
        # falls back to non-streaming if none provided
        streaming_kwargs = dict(
            stream=True,
            callbacks=[StreamingCallbackHandler(new_token_handler)],
        ) if new_token_handler else {}

        # TODO: fix runpod booting issue (15 min+)
        # this is not a working solution
        runpod.api_key = os.getenv("RUNPOD_API_KEY", "EZ2ZWDWQ4ECHHE19WDET114I0EL2SGALIZJO0YNM")
        podid = "bvxte4qal3wv2o"
        inference_server_url = f'https://{podid}-80.proxy.runpod.net'
        
        # inference_server_url = HUGGINGFACE_INFERENCE_ENDPOINT
        
        # headers = {
        #     "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        #     "Content-Type": "application/json",
        # }
        
        # client = Client(inference_server_url, headers=headers)

        # this got called for each inference, or each streaming, in the chat
        llm = HuggingFaceTextGenInference(
            inference_server_url=inference_server_url,
            max_new_tokens=150, # -1 means generate no token
            temperature=0.05, # should be strictly positive
            **streaming_kwargs,
        ) # this is repeatedly called each time, starting from here
        # llm.client = client
        print("starting custom LLM with streaming=true")

    else:
        # falls back to non-streaming if none provided
        streaming_kwargs = dict(
            streaming=True,
            callbacks=[StreamingCallbackHandler(new_token_handler)],
        ) if new_token_handler else {}

        model_kwargs = dict(
            model_name=model_name,
        ) if model_name else {}

        llm = OpenAI(
            temperature=0.0,
            max_tokens=max_tokens,
            **streaming_kwargs,
            **model_kwargs,
        )

    return llm


def get_streaming_chain(prompt, new_token_handler, use_api_chain=False, model_name=None, max_tokens=-1):
    llm = get_streaming_llm(new_token_handler, model_name=model_name, max_tokens=max_tokens)

    if use_api_chain:
        return IndexAPIChain.from_llm(
            llm,
            verbose=True
        )
    else:
        return LLMChain(llm=llm, prompt=prompt, verbose=True)


def get_streaming_tools(tools, new_token_handler):
    streaming_tools = config.initialize_streaming(tools, new_token_handler)
    return streaming_tools


def get_streaming_agent(tools, new_token_handler, model_name=None, **agent_kwargs):
    llm = get_streaming_llm(new_token_handler, model_name=model_name)
    agent = initialize_agent(tools, llm, agent=CUSTOM_AGENT_NAME, **agent_kwargs)
    return agent
