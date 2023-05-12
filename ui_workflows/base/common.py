
import os
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from dataclasses import dataclass

import requests
from utils import  w3
from database.models import db_session, ChatMessage, ChatSession, SystemConfig
from utils import TENDERLY_FORK_URL, w3
from database.models import (MultiStepWorkflow)

TEST_WALLET_CHAIN_ID = 1  # Tenderly Mainnet Fork
TEST_WALLET_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" # vitalik.eth
MOCK_CHAT_MESSAGE_ID = str(uuid.uuid4())
class WorkflowStepClientPayload(TypedDict):
    id: str
    type: str
    status: Literal['pending', 'success', 'error', 'user_interrupt']
    status_message: str
    user_action_data: str
@dataclass
class Result:
    status: Literal['success', 'error']
    description: str
    tx: any = None
    error_msg: Optional[str] = None
    is_approval_tx: bool = False # NOTE: Field deprecated, use Multi-step workflow approach
    parsed_user_request: str = '' # NOTE: Field deprecated, use Multi-step workflow approach

@dataclass
class MultiStepResult:
    status: Literal['success', 'error', 'terminated']
    workflow_id: str
    workflow_type: str
    step_id: str
    step_type: str
    step_number: int
    total_steps: int
    user_action_type: Literal['tx', 'acknowledge']
    tx: Optional[dict] = None
    error_msg: Optional[str] = None
    description: str = ''

@dataclass
class RunnableStep:
    type: str
    user_action_type: Literal['tx', 'acknowledge']
    user_description: str
    function: Callable

@dataclass
class StepProcessingResult:
    status: Literal['success', 'error', 'replace']
    override_user_description: Optional[str] = None
    error_msg: Optional[str] = None
    replace_with_step_type: str = None
    replace_extra_params: Dict = None

class WorkflowValidationError(Exception):
    pass

class WorkflowFailed(Exception):
    pass

def tenderly_simulate_tx(wallet_address, tx):
    payload = {
    "id": 0,
    "jsonrpc": "2.0",
    "method": "eth_sendTransaction",
        "params": [
            {
            "from": wallet_address,
            "to": tx['to'],
            "value": tx['value'] if 'value' in tx else "0x0",
            "data": tx['data'],
            }
        ]
    }
    res = requests.post(TENDERLY_FORK_URL, json=payload)
    res.raise_for_status()

    tx_hash = res.json()['result']
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print("Tenderly TxHash:", tx_hash)

    if receipt['status'] == 0:
        raise Exception(f"Transaction failed, tx_hash: {tx_hash}, check Tenderly dashboard for more details")

def setup_mock_db_objects() -> Dict:
    mock_system_config = SystemConfig(json={})
    db_session.add(mock_system_config)
    db_session.commit()

    mock_chat_session = ChatSession()
    db_session.add(mock_chat_session)
    db_session.commit()
    
    mock_chat_message = ChatMessage(
        actor="user",
        type='text',
        payload="sample text",
        chat_session_id=mock_chat_session.id,
        system_config_id=mock_system_config.id,
    )
    db_session.add(mock_chat_message)
    db_session.commit()
    return  {
        'mock_system_config': mock_system_config,
        'mock_chat_session': mock_chat_session,
        'mock_chat_message': mock_chat_message
    }

def _validate_non_zero_eth_balance(wallet_address):
    if (w3.eth.get_balance(w3.to_checksum_address(wallet_address)) == 0):
        raise WorkflowValidationError("Wallet address has zero ETH balance")


def estimate_gas(tx):
    return hex(w3.eth.estimate_gas(tx))


def compute_abi_abspath(wf_file_path, abi_relative_path):
    return os.path.join(os.path.dirname(os.path.abspath(wf_file_path)), abi_relative_path)

def process_result_and_simulate_tx(wallet_address, result: Union[Result, MultiStepResult]):
    if result.status == "success":
        tenderly_simulate_tx(wallet_address, result.tx)
        print("Workflow successful")
    elif result.status == "terminated":
        print("Workflow terminated as it has reached the final step or user error has occured. See logs for more info.")
    else:
        raise WorkflowFailed(result)

def fetch_multistep_workflow_from_db(id):
    return MultiStepWorkflow.query.filter(MultiStepWorkflow.id == id).first()


def generate_mock_chat_message_id():
    return str(uuid.uuid4())