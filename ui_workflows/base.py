import threading
import time
import sys
import uuid
import os
import json
import traceback
import requests
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from dataclasses import dataclass
from pywalletconnect.client import WCClient
from playwright.sync_api import Playwright, sync_playwright, Page, BrowserContext

import env
from utils import TENDERLY_FORK_URL, w3
from database.models import db_session, WorkflowStep, WorkflowStepStatus, MultiStepWorkflow, ChatMessage, ChatSession, SystemConfig


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
    description: str
    function: Callable

@dataclass
class StepProcessingResult:
    status: Literal['success', 'error']
    error_msg: Optional[str] = None

class WorkflowValidationError(Exception):
    pass


class BaseContractWorkflow(ABC):
    """Common interface for UI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, contract_address: str, abi_path: str, workflow_type: str, workflow_params: Dict) -> None:
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = wallet_address
        self.contract_address = w3.to_checksum_address(contract_address)
        self.abi_path = abi_path
        self.workflow_type = workflow_type
        self.workflow_params = workflow_params
        self.parsed_user_request = f"wf_type: {self.workflow_type}: wf_params:{self.workflow_params}"

    @abstractmethod
    def _run(self) -> Any:
        """Implement the contract interaction logic here."""

    @abstractmethod
    def _pre_workflow_validation(self):
        """Perform any validation before running the workflow."""

    def _load_contract_abi(self):
        """Load contract ABI from file."""
        with open(self.abi_path, 'r') as f:
            self.contract_abi_dict = json.load(f)

    def run(self) -> Any:
        """Main function to call to run the workflow."""
        print(f"Running contract workflow: {self.parsed_user_request}")

        self._load_contract_abi()

        _validate_non_zero_eth_balance(self.wallet_address)
        self._pre_workflow_validation()

        ret = self._run()

        print(f"Contract workflow finished: {self.parsed_user_request}")
        return ret

class BaseContractSingleStepWorkflow(BaseContractWorkflow):
    def __init__(self, wallet_chain_id: int, wallet_address: str, contract_address: str, abi_path: str, user_description: str, workflow_type: str, workflow_params: Dict) -> None:
        self.user_description = user_description
        super().__init__(wallet_chain_id, wallet_address, contract_address, abi_path, workflow_type, workflow_params)

    def run(self) -> Result:
        try:
            return super().run()
        except WorkflowValidationError as e:
            print("CONTRACT SINGLE STEP WORKFLOW VALIDATION ERROR")
            traceback.print_exc()
            return Result(
                status="error", 
                error_msg=e.args[0],
                description=self.user_description
            )
        except Exception as e:
            print("CONTRACT SINGLE STEP WORKFLOW EXCEPTION")
            traceback.print_exc()
            return Result(
                status="error", 
                error_msg="Unexpected error. Check with support.",
                description=self.user_description
            )


class BaseUIWorkflow(ABC):
    """Common interface for UI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, parsed_user_request: str, browser_storage_state: Optional[Dict] = None) -> None:
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = wallet_address
        self.parsed_user_request = parsed_user_request
        self.browser_storage_state = browser_storage_state
        self.thread = None
        self.result_container = []
        self.thread_event = threading.Event()
        self.is_approval_tx = False

    @abstractmethod
    def _run_page(self, page: Page, context: BrowserContext) -> Any:
        """Accept user input and return responses via the send_message function."""

    @abstractmethod
    def _goto_page_and_open_walletconnect(self,page):
        """Go to page and open walletconnect"""

    def _dev_mode_intercept_rpc(self, page) -> None:
        """Intercept RPC calls in dev mode"""
        page.route("**/*", self._intercept_rpc_node_reqs)

    def run(self) -> Any:
        """Spin up headless browser and call run_page function on page."""
        print(f"Running UI workflow: {self.parsed_user_request}")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=_check_headless_allowed())
            context = browser.new_context(storage_state=self.browser_storage_state)
            context.grant_permissions(["clipboard-read", "clipboard-write"])
            page = context.new_page()

            if not env.is_prod():
                self._dev_mode_intercept_rpc(page)

            self._goto_page_and_open_walletconnect(page)
            self._connect_to_walletconnect_modal(page)

            ret = self._run_page(page, context)

            context.close()
            browser.close()
        print(f"UI workflow finished: {self.parsed_user_request}")
        return ret


    def start_listener(self, wc_uri: str) -> None:
        assert self.thread is None, 'not expecting a thread to be started'
        self.thread = threading.Thread(
            target=wc_listen_for_messages,
            args=(self.thread_event, wc_uri, self.wallet_chain_id, self.wallet_address, self.result_container),
        )
        self.thread.start()

    def stop_listener(self) -> Any:
        if self.thread:
            self.thread_event.set()
            self.thread.join()
            self.thread = None
        if self.result_container:
            return self.result_container[-1]
        return None
    
    def _connect_to_walletconnect_modal(self, page):
        page.get_by_text("Copy to clipboard").click()
        wc_uri = page.evaluate("() => navigator.clipboard.readText()")
        self.start_listener(wc_uri)

    def _is_web3_call(self, request) -> Dict[bool, bool]:
        has_list_payload = False
        if request.post_data:
            try:
                payload = json.loads(request.post_data)
                obj_to_check = payload
                if isinstance(payload, list):
                    has_list_payload = True
                    obj_to_check = payload[0]

                if "method" in obj_to_check and obj_to_check["method"].startswith("eth_"):
                    return dict(is_web3_call=True, has_list_payload=has_list_payload)
            except Exception:
                pass
        return dict(is_web3_call=False, has_list_payload=has_list_payload)
    
    def _forward_rpc_node_reqs(self, route):
        route.continue_(url=TENDERLY_FORK_URL)

    def _handle_batch_web3_call(self, route):
        payload = json.loads(route.request.post_data)
        batch_result = []
        for obj in payload:
            response = requests.post(TENDERLY_FORK_URL, json=obj)
            response.raise_for_status()
            batch_result.append(response.json())
        route.fulfill(body=json.dumps(batch_result), headers={"access-control-allow-origin": "*", "access-control-allow-methods": "*", "access-control-allow-headers": "*"})

    def _intercept_rpc_node_reqs(self, route):
        result = self._is_web3_call(route.request)
        if result['is_web3_call']:
            if result['has_list_payload']:
                self._handle_batch_web3_call(route)                
            else:
                self._forward_rpc_node_reqs(route)
        else:
            route.continue_()

class BaseMultiStepWorkflow(BaseUIWorkflow):
    """Common interface for multi-step UI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow: Optional[MultiStepWorkflow], worfklow_params: Dict, curr_step_client_payload: Optional[WorkflowStepClientPayload], runnable_steps: List[RunnableStep]) -> None:
        self.chat_message_id = chat_message_id
        self.workflow = workflow
        self.workflow_type = workflow_type
        self.workflow_params = worfklow_params
        self.runnable_steps = runnable_steps
        self.total_steps = len(runnable_steps)
        self.curr_step_client_payload = curr_step_client_payload

        self.curr_step = None
        self.curr_step_description = None
        browser_storage_state = None
        parsed_user_request = None

        super().__init__(wallet_chain_id, wallet_address, parsed_user_request, browser_storage_state)

    def _run_first_step(self, page, context) -> StepProcessingResult:
        """Run first step"""
        first_step = self.runnable_steps[0]

        # Save step to DB and set current step
        self._create_new_curr_step(first_step.type, 1, first_step.user_action_type, first_step.description)

        return first_step.function(page, context)

    def _run_next_steps(self, page, context) -> StepProcessingResult:
        """Find the next step to run based on the current successful step from client response"""

        curr_runnable_step_index = [i for i,s in enumerate(self.runnable_steps) if s.type == self.curr_step.type][0]
        next_step_to_run_index = curr_runnable_step_index + 1
        next_step_to_run = self.runnable_steps[next_step_to_run_index]

        # Save step to DB and reset current step
        self._create_new_curr_step(next_step_to_run.type, next_step_to_run_index + 1, next_step_to_run.user_action_type, next_step_to_run.description)

        return next_step_to_run.function(page, context)


    def run(self) -> Any:
        try:
            self._setup_workflow()

            if(not self._validate_before_page_run()):
                print("Multi-step Workflow terminated before page run")
                return MultiStepResult(
                    status='terminated',
                    workflow_id=str(self.workflow.id),
                    workflow_type=self.workflow_type,
                    step_id=str(self.curr_step.id),
                    step_type=self.curr_step.type,
                    user_action_type=self.curr_step.user_action_type.name,
                    step_number=self.curr_step.step_number,
                    total_steps=self.total_steps,
                    tx=None,
                    description=self.curr_step_description
                )
            
            return super().run()
        except Exception:
            print("MULTISTEP WORKFLOW EXCEPTION")
            traceback.print_exc()
            self.stop_listener()
            return MultiStepResult(
                status='error',
                workflow_id=str(self.workflow.id),
                workflow_type=self.workflow_type,
                step_id=str(self.curr_step.id) if self.curr_step else None,
                step_type=self.curr_step.type if self.curr_step else None,
                user_action_type=self.curr_step.user_action_type.name if self.curr_step else None,
                step_number=self.curr_step.step_number if self.curr_step else None,
                total_steps=self.total_steps,
                tx=None,
                error_msg="Unexpected error. Check with support.",
                description=self.curr_step_description
            )

    def _setup_workflow(self):
        """
        This setup function does the following primary tasks:
        1. Create new workflow in DB if not already created
        2. Use current step payload/feedback from client to get the step's browser storage state so that it can be injected into the browser context to be used in next step
        3. User current step payload/feedback from client and save it to DB
        4. Set parsed_user_request to be used for logging
        """
        if not self.workflow:
            # Create new workflow in DB
            self.workflow = MultiStepWorkflow(
                chat_message_id=self.chat_message_id,
                wallet_chain_id=self.wallet_chain_id,
                wallet_address=self.wallet_address,
                type=self.workflow_type,
                params=self.workflow_params,
            )
            self._save_to_db([self.workflow])
        
        if self.curr_step_client_payload:
            self.curr_step = WorkflowStep.query.filter(WorkflowStep.id == self.curr_step_client_payload['id']).first()
            # Retrive browser storage state from DB for next step
            self.browser_storage_state = self.curr_step.step_state['browser_storage_state'] if  self.curr_step.step_state else None

            # Save current step status and user action data to DB that we receive from client
            self.curr_step.status = WorkflowStepStatus[self.curr_step_client_payload['status']]
            self.curr_step.status_message = self.curr_step_client_payload['statusMessage']
            self.curr_step.user_action_data = self.curr_step_client_payload['userActionData']
            self._save_to_db([self.curr_step])

        self.parsed_user_request = f"chat_message_id: {self.chat_message_id}, wf_id: {self.workflow.id}, workflow_type: {self.workflow_type}, curr_step_type: {self.curr_step.type if self.curr_step else None} params: {self.workflow_params}"

    def _validate_before_page_run(self) -> bool:
        # Perform validation to check if we can continue with next step
        if self.curr_step:
            if self.curr_step.status != WorkflowStepStatus.success:
                print("Workflow step recorded an unsuccessful status from client")
                return False
            
            if self.curr_step.step_number == self.total_steps:
                print("Workflow has completed all steps")
                return False
        return True
    
    def _run_page(self, page, context) -> MultiStepResult:
        if not self.curr_step:
            processing_result = self._run_first_step(page, context)
        else:
            processing_result = self._run_next_steps(page, context)

        if processing_result.status == 'error':
            self.curr_step.status = WorkflowStepStatus.error
            self.curr_step.status_message = processing_result.error_msg
            self._save_to_db([self.curr_step])
        
        # Arbitrary wait to allow for enough time for WalletConnect relay to send our client the tx data
        page.wait_for_timeout(5000)
        tx = self.stop_listener()
        return MultiStepResult(
            status=processing_result.status,
            workflow_id=str(self.workflow.id),
            workflow_type=self.workflow_type,
            step_id=str(self.curr_step.id),
            step_type=self.curr_step.type,
            user_action_type=self.curr_step.user_action_type.name,
            step_number=self.curr_step.step_number,
            total_steps=self.total_steps,
            tx=tx,
            error_msg=processing_result.error_msg,
            description=self.curr_step_description
        )

    def _save_to_db(self, models: List[any]) -> None:
        db_session.add_all(models)
        db_session.commit()

    def _preserve_browser_local_storage_item(self, context, key):
        storage_state = self._get_browser_cookies_and_storage(context)
        local_storage = storage_state['origins'][0]['localStorage']
        origin = storage_state['origins'][0]['origin']
        item_to_preserve = None
        for item in local_storage:
            if item['name'] == key:
                item_to_preserve = item
                break
        storage_state_to_save = {'origins': [{'origin': origin, 'localStorage': [item_to_preserve]}]}

        step_state = {
            "browser_storage_state": storage_state_to_save
        }

        self._update_step_state(step_state)

    def _create_new_curr_step(self, step_type: str, step_number: int, user_action_type: Literal['tx', 'acknowledge'], step_description, step_state: Dict = {}) -> WorkflowStep:
        workflow_step = WorkflowStep(
            workflow_id=self.workflow.id,
            type=step_type,
            step_number=step_number,
            status=WorkflowStepStatus.pending,
            user_action_type=user_action_type,
            step_state=step_state
        )
        self._save_to_db([workflow_step])
        self.curr_step = workflow_step
        self.curr_step_description = step_description
        return workflow_step
    
    def _get_step_by_id(self, step_id: str) -> WorkflowStep:
        return WorkflowStep.query.filter(WorkflowStep.id == step_id).first()
    
    def _update_step_state(self, step_state = {}):
        if not self.curr_step.step_state:
            self.curr_step.step_state = step_state
        else:
            self.curr_step.step_state.update(step_state)
        self._save_to_db([self.curr_step])

    def _get_browser_cookies_and_storage(self, context) -> Dict:
        return context.storage_state()


def _check_headless_allowed():
    # Headless cannot be used if on Mac, otherwise pyperclip doesn't work
    return sys.platform == 'linux'


def wc_listen_for_messages(
        thread_event: threading.Event, wc_uri: str, wallet_chain_id: int, wallet_address: str, result_container: List):
    # Connect to WC URI using wallet address
    wclient = WCClient.from_wc_uri(wc_uri)
    print("Connecting with the Dapp ...")
    session_data = wclient.open_session()
    wclient.reply_session_request(session_data[0], wallet_chain_id, wallet_address)
    print("Wallet Connected.")

    print(" To quit : Hit CTRL+C, or disconnect from Dapp.")
    print("Now waiting for dapp messages ...")
    while not thread_event.is_set():
        try:
            time.sleep(0.3)
            # get_message return : (id, method, params) or (None, "", [])
            read_data = wclient.get_message()
            if read_data[0] is not None:
                print("\n <---- Received WalletConnect wallet query :")

                if (
                    read_data[1] == "eth_sendTransaction"
                ):
                    # Get transaction params
                    tx = read_data[2][0]
                    print("TX:", tx)
                    result_container.append(tx)
                    break

                # Detect quit
                #  v1 disconnect
                if (
                    read_data[1] == "wc_sessionUpdate"
                    and read_data[2][0]["approved"] == False
                ):
                    print("User disconnects from Dapp (WC v1).")
                    break
                #  v2 disconnect
                if read_data[1] == "wc_sessionDelete" and read_data[2].get("message"):
                    print("User disconnects from Dapp (WC v2).")
                    print("Reason :", read_data[2]["message"])
                    break
        except KeyboardInterrupt:
            print("Demo interrupted.")
            break
    wclient.close()
    print("WC disconnected.")


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