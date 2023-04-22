from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from dataclasses import dataclass
import threading
import time
import sys
import uuid
import traceback
import requests
from pywalletconnect.client import WCClient
from playwright.sync_api import Playwright, sync_playwright, Page, BrowserContext

import env
from utils import TENDERLY_FORK_URL
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
    parsed_user_request: str
    description: str
    tx: any = None
    is_approval_tx: bool = False
    error_msg: Optional[str] = None

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
class StepProcessingResult:
    status: Literal['success', 'error']
    error_msg: Optional[str] = None

class BaseUIWorkflow(ABC):
    """Common interface for UI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, parsed_user_request: str, rpc_urls_to_intercept: List[str], browser_storage_state=None) -> None:
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = wallet_address
        self.parsed_user_request = parsed_user_request
        self.rpc_urls_to_intercept = rpc_urls_to_intercept
        self.browser_storage_state = browser_storage_state
        self.thread = None
        self.result_container = []
        self.thread_event = threading.Event()
        self.is_approval_tx = False

    @abstractmethod
    def _run_page(self, page: Page, context: BrowserContext) -> Any:
        """Accept user input and return responses via the send_message function."""

    def _dev_mode_intercept_rpc(self, page) -> None:
        """Intercept RPC calls in dev mode"""
        for url in self.rpc_urls_to_intercept:
            page.route(url, self._handle_rpc_node_reqs)

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
    
    def _handle_rpc_node_reqs(self, route):
        post_body = route.request.post_data
        # Forward request to Tenderly RPC node
        data = requests.post(TENDERLY_FORK_URL, data=post_body)
        route.fulfill(body=data.text, headers={"access-control-allow-origin": "*", "access-control-allow-methods": "*", "access-control-allow-headers": "*"})
    
    def _connect_to_walletconnect_modal(self, page):
        page.get_by_text("Copy to clipboard").click()
        wc_uri = page.evaluate("() => navigator.clipboard.readText()")
        self.start_listener(wc_uri)

class BaseMultiStepWorkflow(BaseUIWorkflow):
    """Common interface for multi-step UI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow: Optional[MultiStepWorkflow], worfklow_params: Dict, curr_step_client_payload: Optional[WorkflowStepClientPayload], rpc_urls_to_intercept: List[str], total_steps: int) -> None:
        self.chat_message_id = chat_message_id
        self.workflow = workflow
        self.workflow_type = workflow_type
        self.workflow_params = worfklow_params
        self.total_steps = total_steps

        self.curr_step = None
        self.curr_step_description = None
        browser_storage_state = None

        if not workflow:
            # Create new workflow in DB
            self.workflow = MultiStepWorkflow(
                chat_message_id=self.chat_message_id,
                wallet_chain_id=wallet_chain_id,
                wallet_address=wallet_address,
                type=self.workflow_type,
                params=self.workflow_params,
            )
            self._save_to_db([self.workflow])
        
        if curr_step_client_payload:
            self.curr_step = WorkflowStep.query.filter(WorkflowStep.id == curr_step_client_payload['id']).first()
            # Retrive browser storage state from DB for next step
            browser_storage_state = self.curr_step.step_state['browser_storage_state'] if  self.curr_step.step_state else None

            # Save current step status and user action data to DB that we receive from client
            self.curr_step.status = WorkflowStepStatus[curr_step_client_payload['status']]
            self.curr_step.status_message = curr_step_client_payload['status_message']
            self.curr_step.user_action_data = curr_step_client_payload['user_action_data']
            self._save_to_db([self.curr_step])

        parsed_user_request = f"chat_message_id: {self.chat_message_id}, wf_id: {self.workflow.id}, workflow_type: {self.workflow_type}, curr_step_type: {self.curr_step.type if self.curr_step else None} params: {self.workflow_params}"

        super().__init__(wallet_chain_id, wallet_address, parsed_user_request, rpc_urls_to_intercept, browser_storage_state)

    def run(self) -> Any:
        try:
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
        except Exception as e:
            print("MULTISTEP WORKFLOW EXCEPTION")
            traceback.print_exc()
            self.stop_listener()
            return MultiStepResult(
                status='error',
                workflow_id=str(self.workflow.id),
                workflow_type=self.workflow_type,
                step_id=str(self.curr_step.id),
                step_type=self.curr_step.type,
                user_action_type=self.curr_step.user_action_type.name,
                step_number=self.curr_step.step_number,
                total_steps=self.total_steps,
                tx=None,
                error_msg="Unexpected error",
                description=self.curr_step_description
            )


    @abstractmethod
    def _goto_page_and_setup_walletconnect(self,page):
        """Go to page and setup walletconnect"""

    @abstractmethod
    def _initialize_workflow_for_first_step(self, page, context) -> StepProcessingResult:
        """Initialize workflow and create first step"""

    @abstractmethod
    def _perform_next_steps(self, page) -> StepProcessingResult:
        """Plan next steps based on successful execution of current step"""

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
        self._goto_page_and_setup_walletconnect(page)
        
        if not self.curr_step:
            processing_result = self._initialize_workflow_for_first_step(page, context)
        else:
            processing_result = self._perform_next_steps(page)

        if processing_result.status == 'error':
            self.curr_step.status = WorkflowStepStatus.error
            self.curr_step.status_message = processing_result.error_msg
            self._save_to_db([self.curr_step])
        
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

    def _create_new_curr_step(self, step_type: str, step_number: int, user_action_type: Literal['tx', 'acknowledge'], step_description, step_state: Dict = None) -> WorkflowStep:
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


def tenderly_simulate_tx(tenderly_api_access_key, wallet_address, tx):
    tenderly_simulate_url = 'https://api.tenderly.co/api/v1/account/Yield/project/chatweb3/fork/902db63e-9c5e-415b-b883-5701c77b3aa7/simulate'

    payload = {
      "save": True, 
      "save_if_fails": True, 
      "simulation_type": "full",
      'network_id': '1',
      'from': wallet_address,
      'to': tx['to'],
      'input': tx['data'],
      'gas': int(tx['gas'], 16),
      'value': int(tx['value'], 16) if 'value' in tx else 0,
    }

    res = requests.post(tenderly_simulate_url, json=payload, headers={'X-Access-Key': tenderly_api_access_key })
    res.raise_for_status()

    print("Tenderly Simulation ID: ", res.json()["simulation"]["id"])


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