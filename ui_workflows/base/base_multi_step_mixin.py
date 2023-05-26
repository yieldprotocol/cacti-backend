


import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from web3 import Web3

from utils import estimate_gas
from database.models import db_session, WorkflowStep, WorkflowStepStatus, MultiStepWorkflow

from enum import Enum

from .common import WorkflowStepClientPayload, RunnableStep, ContractStepProcessingResult, MultiStepResult, WorkflowValidationError, StepProcessingResult
from .base_contract_workflow import BaseContractWorkflow
from .base_ui_workflow import BaseUIWorkflow
from .base_contract_workflow import BaseContractWorkflow

class WorkflowApproach(Enum):
    UI = 1
    CONTRACT = 2

class BaseMultiStepMixin():
    """Mixin inherited by both 'BaseMultiStepUIWorkflow' and 'BaseMultiStepContractWorkflow' to hold common code for multi-step UI and Contract workflows"""

    def __init__(self, workflow_approach: WorkflowApproach, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, multistep_workflow: Optional[MultiStepWorkflow], workflow_params: Dict, curr_step_client_payload: Optional[WorkflowStepClientPayload], runnable_steps: List[RunnableStep], final_step_type) -> None:
        self.workflow_approach = workflow_approach

        if self.workflow_approach == WorkflowApproach.UI:
            self.super_base_class = BaseUIWorkflow
        else:
            self.super_base_class = BaseContractWorkflow

        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.chat_message_id = chat_message_id
        self.workflow_type = workflow_type
        self.workflow_params = workflow_params

        self.multistep_workflow = multistep_workflow
        self.multistep_workflow_id = multistep_workflow.id if multistep_workflow else str(uuid.uuid4()) # When this workflow is initiated for the first time, there will not be a multistep workflow record in DB yet so we initialize the ID here with a random UUID which will be stored later in the DB when the workflow is saved
        self.workflow_type = workflow_type
        self.workflow_params = workflow_params
        self.runnable_steps = runnable_steps
        self.curr_step_client_payload = curr_step_client_payload
        self.final_step_type = final_step_type
        
        self.curr_step: Optional[WorkflowStep] = None
        self.curr_step_description = None
        self.prev_step: Optional[WorkflowStep] = None


    def run(self) -> MultiStepResult:
        start_log_params = f"{self.workflow_type}, chat_message_id: {self.chat_message_id}, multistep_wf_id: {self.multistep_workflow_id}, curr_step_id: {self.curr_step_client_payload['id'] if self.curr_step_client_payload else None}, curr_step_type: {self.curr_step_client_payload['type'] if self.curr_step_client_payload else self.runnable_steps[0].type}, wf_params: {self.workflow_params}"
        approach_label = 'UI' if self.workflow_approach == WorkflowApproach.UI else 'CONTRACT'
        print(f"Multi-step {approach_label} workflow started, wf_type: {start_log_params}")
        try:
            self._setup_workflow()

            if(self._check_should_terminate_run()):
                print(f"Multi-step {approach_label} Workflow terminated before run, {start_log_params}")
                return MultiStepResult(
                    status='terminated',
                    workflow_id=str(self.multistep_workflow.id),
                    workflow_type=self.workflow_type,
                    step_id=str(self.curr_step.id),
                    step_type=self.curr_step.type,
                    user_action_type=self.curr_step.user_action_type.name,
                    step_number=self.curr_step.step_number,
                    is_final_step=self._check_is_final_step(),
                    tx=None,
                    description=self.curr_step_description
                )                

            return self.super_base_class.run(self)
        except WorkflowValidationError as e:
            print(f"MULTISTEP {approach_label} WORKFLOW VALIDATION ERROR, {start_log_params}")
            return self._create_error_result(e.args[0])

        except Exception:
            print(f"MULTISTEP {approach_label} WORKFLOW EXCEPTION, {start_log_params}")
            traceback.print_exc()
            return self._create_error_result("Unexpected error. Check with support.")

        finally:
            if self.workflow_approach == WorkflowApproach.UI:
                self.stop_wallet_connect_listener()

            end_log_params = f"wf_type: {self.workflow_type}, chat_message_id: {self.chat_message_id}, multistep_wf_id: {self.multistep_workflow_id}, curr_step_id: {self.curr_step.id if self.curr_step else None}, curr_step_type: {self.curr_step.type if self.curr_step else self.runnable_steps[0].type}"
            print(f"Multi-step {approach_label} workflow ended, {end_log_params}")

    # TODO: only in UI
    # def _run_page(self, page, context) -> MultiStepResult:

    def _run(self, *args, **kwargs) -> MultiStepResult:
        processing_result = self._run_step(*args, **kwargs)

        if processing_result.status == 'error':
            self.curr_step.status = WorkflowStepStatus.error
            self.curr_step.status_message = processing_result.error_msg
            self._save_to_db([self.curr_step])

        if self.workflow_approach == WorkflowApproach.UI:
            # For UI approach, perform additional page operations
            page = args[0]
            browser_context = args[1]

            # Arbitrary wait to allow for enough time for WalletConnect relay to send our client the tx data
            page.wait_for_timeout(5000)

            # Stop WC listener thread and extract tx data if any
            tx = self.stop_wallet_connect_listener()

            if tx['gas'] == '0x0':
                try:
                    tx['from'] = Web3.to_checksum_address(tx['from'])
                    tx['to'] = Web3.to_checksum_address(tx['to'])
                    tx['gas'] = estimate_gas(tx)
                except Exception:
                    # If no gas specified by protocol UI and gas estimation fails, use arbitary gas limit 500,000
                    tx['gas'] = "0x7A120" 
        else:
            # For contract ABI approach
            tx = processing_result.tx
            tx['gas'] = estimate_gas(tx)

        if tx and "value" not in tx:
            tx['value'] = "0x0"

        computed_user_description = processing_result.override_user_description or self.curr_step_description

        return MultiStepResult(
            status=processing_result.status,
            workflow_id=str(self.multistep_workflow.id),
            workflow_type=self.workflow_type,
            step_id=str(self.curr_step.id),
            step_type=self.curr_step.type,
            user_action_type=self.curr_step.user_action_type.name,
            step_number=self.curr_step.step_number,
            is_final_step=self._check_is_final_step(),
            tx=tx,
            error_msg=processing_result.error_msg,
            description=computed_user_description
        )

    def _run_step(self, *args, **kwargs) -> Union[ContractStepProcessingResult, StepProcessingResult]:
        replacement_step_type = kwargs.get('replacement_step_type')
        extra_params = kwargs.get('extra_params')

        if self.workflow_approach == WorkflowApproach.UI:
            page = args[0]
            browser_context = args[1]

        if replacement_step_type:
            result = self._handle_step_replace(*args, **kwargs)
        elif not self.curr_step:
            result = self._run_first_step(*args, **kwargs)
        else:
            self.prev_step = self.curr_step
            result = self._run_next_step(*args, **kwargs)

        if result.status == 'replace':
            if self.workflow_approach == WorkflowApproach.UI:
                return self._run_step(page, browser_context, replacement_step_type=result.replace_with_step_type, extra_params=result.replace_extra_params)
            else:
                return self._run_step(replacement_step_type=result.replace_with_step_type, extra_params=result.replace_extra_params)
        else:
            return result

    def _run_first_step(self, *args, **kwargs) -> Union[ContractStepProcessingResult, StepProcessingResult]:
        """Run first step, it is singled out as this is the only step that has no prior client response to process unlike other steps"""
        first_step = self.runnable_steps[0]

        # Save step to DB and set current step
        self._create_new_curr_step(first_step.type, 1, first_step.user_action_type, first_step.user_description)

        return first_step.function(*args, **kwargs)

    def _run_next_step(self, *args, **kwargs) -> Union[ContractStepProcessingResult, StepProcessingResult]:
        """Find the next step to run based on the current successful step from client response"""
        curr_runnable_step_index = self._find_runnable_step_index_by_step_type(self.curr_step.type)
        next_step_to_run_index = curr_runnable_step_index + 1
        next_step_to_run = self.runnable_steps[next_step_to_run_index]
        prev_step = self.curr_step

        # Save step to DB and reset current step
        self._create_new_curr_step(next_step_to_run.type, next_step_to_run_index + 1, next_step_to_run.user_action_type, next_step_to_run.user_description)

        log_params = f"wf_type: {self.workflow_type}, chat_message_id: {self.chat_message_id}, multistep_wf_id: {self.multistep_workflow_id}, curr_step_id: {self.curr_step.id}, curr_step_type: {self.curr_step.type}, prev_step_type: {prev_step.type}"

        print("Multi-step contract workflow - running next step, ", log_params)

        return next_step_to_run.function(*args, **kwargs)

    def _handle_step_replace(self, *args, **kwargs) -> Union[ContractStepProcessingResult, StepProcessingResult]:
        replacement_step_type: str = kwargs.get('replacement_step_type')
        replacement_extra_params: Dict = kwargs.get('extra_params')

        if self.workflow_approach == WorkflowApproach.UI:
            page = args[0]
            browser_context = args[1]

        print(f"Workflow step replacement being processed, wf_type: {self.workflow_type}, multistep_wf_id: {self.multistep_workflow_id}, curr_step_id: {self.curr_step.id}, from_step_type: {self.curr_step.type}, to_step_type: {replacement_step_type}")

        runnable_step_index = self._find_runnable_step_index_by_step_type(replacement_step_type)
        runnable_step = self.runnable_steps[runnable_step_index]

        self.curr_step.type = runnable_step.type
        self.curr_step.user_action_type = runnable_step.user_action_type
        self._save_to_db([self.curr_step])

        self.curr_step_description = runnable_step.user_description

        if self.workflow_approach == WorkflowApproach.UI:
            return runnable_step.function(page, browser_context, replacement_extra_params)
        else:
            return runnable_step.function(replacement_extra_params)
        
    def _find_runnable_step_index_by_step_type(self, step_type) -> int:
        return [i for i,s in enumerate(self.runnable_steps) if s.type == step_type][0]

    def _setup_workflow(self):
        """
        This setup function does the following primary tasks:
        1. Create new workflow in DB if not already created
        2. Use current step payload/feedback from client to get the step's browser storage state so that it can be injected into the browser context to be used in next step
        3. User current step payload/feedback from client and save it to DB
        4. Set log_params to be used for logging
        """
        if not self.multistep_workflow:
            # Create new workflow in DB
            self.multistep_workflow = MultiStepWorkflow(
                id=self.multistep_workflow_id,
                chat_message_id=self.chat_message_id,
                wallet_chain_id=self.wallet_chain_id,
                wallet_address=self.wallet_address,
                type=self.workflow_type,
                params=self.workflow_params,
            )
            self._save_to_db([self.multistep_workflow])
        
        if self.curr_step_client_payload:
            self.curr_step: WorkflowStep = WorkflowStep.query.filter(WorkflowStep.id == self.curr_step_client_payload['id']).first()
            # Retrive browser storage state from DB for next step

            if self.curr_step.status != WorkflowStepStatus.pending:
                raise WorkflowValidationError("Current step is not in pending status which means it has already been processed, FE client should not be sending a payload for this step")

            # TODO: only in UI
            self.browser_storage_state = self.curr_step.step_state['browser_storage_state'] if  self.curr_step.step_state else None

            # Save current step status and user action data to DB that we receive from client
            self.curr_step.status = WorkflowStepStatus[self.curr_step_client_payload['status']]
            self.curr_step.status_message = self.curr_step_client_payload['statusMessage']

            # If user action data is missing it means that the client response payload is of an unsuccessful status such as 'error'
            if self.curr_step_client_payload.get('userActionData'):
                self.curr_step.user_action_data = self.curr_step_client_payload['userActionData']

            self._save_to_db([self.curr_step])

    def _check_should_terminate_run(self) -> bool:
        # Perform checks to see if we can continue with next step
        if self.curr_step:
            if self.curr_step.status != WorkflowStepStatus.success:
                print("Workflow step recorded an unsuccessful status from client")
                return True
            
            if self._check_is_final_step():
                print("Workflow has completed all steps")
                return True
        return False

    def _check_is_final_step(self) -> bool:
        if not self.curr_step:
            return self.runnable_steps[0].type == self.final_step_type
        
        return self.curr_step.type == self.final_step_type

    def _save_to_db(self, models: List[any]) -> None:
        db_session.add_all(models)
        db_session.commit()

    def _create_new_curr_step(self, step_type: str, step_number: int, user_action_type: Literal['tx', 'acknowledge'], step_description, step_state: Dict = {}) -> WorkflowStep:
        workflow_step = WorkflowStep(
            workflow_id=self.multistep_workflow.id,
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

    def _create_error_result(self, error_msg: str):
        return MultiStepResult(
            status='error',
            workflow_id=str(self.multistep_workflow.id),
            workflow_type=self.workflow_type,
            step_id=str(self.curr_step.id) if self.curr_step else None,
            step_type=self.curr_step.type if self.curr_step else None,
            user_action_type=self.curr_step.user_action_type.name if self.curr_step else None,
            step_number=self.curr_step.step_number if self.curr_step else None,
            is_final_step=self._check_is_final_step(),
            tx=None,
            error_msg=error_msg,
            description=self.curr_step_description or "(Unexpected error)"
        )