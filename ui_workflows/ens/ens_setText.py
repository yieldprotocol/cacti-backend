import re
from logging import basicConfig, INFO
import time
import json
import uuid
import os
import requests
import sha3 # 'pip install pysha3'
from idna import encode, IDNAError

from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import env
from utils import TENDERLY_FORK_URL, w3
from ..base import BaseUIWorkflow, MultiStepResult, BaseMultiStepWorkflow, WorkflowStepClientPayload, StepProcessingResult, RunnableStep, tenderly_simulate_tx, setup_mock_db_objects, Result
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)


def keccak_256(data):
    k = sha3.keccak_256()
    k.update(data)
    return k.hexdigest()

def to_unicode(name):
    try:
        return encode(name, uts46=True, transitional=False, std3_rules=True).decode('utf-8')
    except IDNAError as e:
        return name

def namehash(input_name):
    node = bytes.fromhex("00" * 32)

    name = to_unicode(input_name)

    if name:
        labels = name.split(".")

        for label in reversed(labels):
            label_sha = bytes.fromhex(keccak_256(label.encode()))
            node_sha = keccak_256(node + label_sha)
            node = bytes.fromhex(node_sha)

    return "0x" + node.hex()


class ENSSetText():
    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, params: Dict) -> None:
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = wallet_address
        self.chat_message_id = chat_message_id
        self.params = params
        self.parsed_user_request = f"{params["name"]}: set {params["key"]} to {params["value"]}"


    def run() -> Result:
        node = namehash(name)
        contract_address = "0x4976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41"
        # Create a contract object
        contract = w3.eth.contract(address=Web3.toChecksumAddress(contract_address), abi=contract_abi_dict)
        # Construct the transaction input data
        tx = contract.encodeABI(fn_name='setText', args=[node, key, value])
        # return the transaction input

        return Result(
                status="success", 
                tx=tx,
                is_approval_tx=False, 
                parsed_user_request=self.parsed_user_request,
                description=description
            )


# Invoke this with python3 -m ui_workflows.ens.ens_setText
if __name__ == "__main__":
    tenderly_api_access_key = os.environ.get("TENDERLY_API_ACCESS_KEY", None)
    ens_to_set = "vitalik.eth"
    wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    params: Dict = {"name": "vitalik.eth", "key":"url", "value":"https://twitter.com/VitalikButerin"}
    result: Result = ENSSetText(wallet_chain_id, wallet_address, mock_message_id, params)

    tenderly_simulate_tx(tenderly_api_access_key, wallet_address, result.tx)
    print(result)