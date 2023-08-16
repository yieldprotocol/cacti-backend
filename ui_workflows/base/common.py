
import os
import uuid
import json
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from dataclasses import dataclass
from web3 import Web3

import requests
import context
from utils import TENDERLY_API_KEY, TENDERLY_PROJECT_API_BASE_URL, TENDERLY_DASHBOARD_PROJECT_BASE_URL
from database.models import db_session, ChatMessage, ChatSession, SystemConfig
from database.models import (MultiStepWorkflow)

TEST_WALLET_CHAIN_ID = 1  # Tenderly Mainnet Fork
TEST_WALLET_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" # vitalik.eth
MOCK_CHAT_MESSAGE_ID = str(uuid.uuid4())
ERC20_ABI = [ { "inputs": [ { "internalType": "address", "name": "spender", "type": "address" }, { "internalType": "uint256", "name": "value", "type": "uint256" } ], "name": "approve", "outputs": [{ "internalType": "bool", "name": "", "type": "bool" }], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [ { "internalType": "address", "name": "owner", "type": "address" }, { "internalType": "address", "name": "spender", "type": "address" } ], "name": "allowance", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" } ]
USDC_ADDRESS = Web3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")

# Response from FE Client for a particular step, contains user's action data eg. if user confirmed a tx, then tx status and tx hash
class WorkflowStepClientPayload(TypedDict):
    id: str
    type: str
    status: Literal['pending', 'success', 'error', 'user_interrupt']
    statusMessage: str
    userActionData: str
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
    user_action_type: Literal['tx', 'acknowledge']
    is_final_step: bool = False
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

@dataclass
class ContractStepProcessingResult(StepProcessingResult):
    tx: Optional[dict] = None

class WorkflowValidationError(Exception):
    pass

class WorkflowFailed(Exception):
    pass

def tenderly_simulate_tx_on_fork(wallet_address: str, tx: Dict) -> str:    
    payload = {
    "jsonrpc": "2.0",
    "method": "eth_sendTransaction",
        "params": [
            {
                "from": wallet_address,
                "to": tx['to'],
                "value": tx['value'] if 'value' in tx else "0x0",
                "data": tx['data'],
                "gas": tx['gas'],
            }
        ]
    }

    fork_id = context.get_web3_fork_id()
    fork_rpc_url = context.get_web3_tenderly_fork_url()

    res = requests.post(fork_rpc_url, json=payload)
    res.raise_for_status()

    tx_hash = res.json()['result']

    fork_web3 = Web3(Web3.HTTPProvider(fork_rpc_url))
    receipt = fork_web3.eth.wait_for_transaction_receipt(tx_hash)

    tenderly_simulation_id = get_latest_simulation_id_on_fork(fork_rpc_url)

    tenderly_dashboard_link = f"{TENDERLY_DASHBOARD_PROJECT_BASE_URL}/fork/{fork_id}/simulation/{tenderly_simulation_id}"

    print("Tenderly simulation dashboard link:", tenderly_dashboard_link)

    # Tx Error handling
    if receipt['status'] == 0:
        tenderly_simulation_api = f"{TENDERLY_PROJECT_API_BASE_URL}/fork/{fork_id}/simulation/{tenderly_simulation_id}"
        res = requests.get(tenderly_simulation_api, headers={'X-Access-Key': TENDERLY_API_KEY})
        error_message = 'n/a'
        if res.status_code == 200:
            simulation_data = res.json()
            error_message = simulation_data['transaction']['error_message']
        raise Exception(f"Transaction failed, error_message: {error_message}, check fork for more details - {tenderly_dashboard_link}")
    
    return tx_hash

def get_latest_simulation_on_fork(fork_rpc_url):
    get_latest_tx_payload = {
        "jsonrpc": "2.0",
        "method": "evm_getLatest",
        "params": []
    }

    res = requests.post(fork_rpc_url, json=get_latest_tx_payload)
    res.raise_for_status()

    return res.json()

def get_latest_simulation_id_on_fork(fork_rpc_url):
    return get_latest_simulation_on_fork(fork_rpc_url)['result']

def advance_fork_blocks(num_blocks) -> None:
    fork_rpc_url = context.get_web3_tenderly_fork_url()

    payload = {
        "jsonrpc": "2.0",
        "method": "evm_increaseBlocks",
        "params": [
            hex(num_blocks)
        ]
    }

    res = requests.post(fork_rpc_url, json=payload)
    res.raise_for_status()

def advance_fork_time_secs(secs) -> None:
    fork_rpc_url = context.get_web3_tenderly_fork_url()

    payload = {
        "jsonrpc": "2.0",
        "method": "evm_increaseTime",
        "params": [
            hex(secs)
        ]
    }

    res = requests.post(fork_rpc_url, json=payload)
    res.raise_for_status()

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
    web3_provider = context.get_web3_provider()
    if (web3_provider.eth.get_balance(web3_provider.to_checksum_address(wallet_address)) == 0):
        raise WorkflowValidationError("Wallet address has zero ETH balance")

def compute_abi_abspath(wf_file_path, abi_relative_path):
    return os.path.join(os.path.dirname(os.path.abspath(wf_file_path)), abi_relative_path)

def process_result_and_simulate_tx(wallet_address, result: Union[Result, MultiStepResult]) -> Optional[str]:
    if result.status == "success":
        tx_hash = tenderly_simulate_tx_on_fork(wallet_address, result.tx)
        print("Workflow successful")
        return tx_hash
    elif result.status == "terminated":
        print("Workflow terminated as it has reached the final step or user error has occured. See logs for more info.")
    else:
        raise WorkflowFailed(result)
    return None

def fetch_multi_step_workflow_from_db(id):
    return MultiStepWorkflow.query.filter(MultiStepWorkflow.id == id).first()

def generate_mock_chat_message_id():
    return str(uuid.uuid4())

def revoke_erc20_approval(token_address: str, owner_address: str, spender_address: str):
    print(f"Revoking ERC20 approval, owner_address: {owner_address}, spender_address: {spender_address}, token_address: {token_address}")
    set_erc20_allowance(token_address, owner_address, spender_address, 0)

def set_erc20_allowance(token_address: str, owner_address: str, spender_address: str, amount: int):
    print(f"Setting ERC20 allowance, owner_address: {owner_address}, spender_address: {spender_address}, token_address: {token_address}, amount: {amount}")
    web3_provider = context.get_web3_provider()
    contract = web3_provider.eth.contract(Web3.to_checksum_address(token_address), abi=json.dumps(ERC20_ABI))

    tx_hash = contract.functions.approve(Web3.to_checksum_address(spender_address), amount).transact({'from': Web3.to_checksum_address(owner_address), 'to': token_address, 'gas': "0x0"})

    tx_receipt = web3_provider.eth.wait_for_transaction_receipt(tx_hash)