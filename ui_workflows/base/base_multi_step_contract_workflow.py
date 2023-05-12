import traceback
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from database.models import db_session, WorkflowStep, WorkflowStepStatus, MultiStepWorkflow

from .common import WorkflowStepClientPayload, RunnableStep, StepProcessingResult, MultiStepResult
from .base_contract_workflow import BaseContractWorkflow

class BaseMultiStepContractWorkflow(BaseContractWorkflow):
    """Base class for multi-step contract workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow: Optional[MultiStepWorkflow], workflow_params: Dict, curr_step_client_payload: Optional[WorkflowStepClientPayload], runnable_steps: List[RunnableStep], contract_address: str, abi_path: str) -> None:
        self.chat_message_id = chat_message_id
        self.workflow = workflow
        self.workflow_type = workflow_type
        self.workflow_params = workflow_params
        self.runnable_steps = runnable_steps
        self.total_steps = len(runnable_steps)
        self.curr_step_client_payload = curr_step_client_payload

        self.curr_step = None
        self.curr_step_description = None

        # NOTE: UI
        # browser_storage_state = None
        # parsed_user_request = None

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, contract_address, abi_path, workflow_type, workflow_params)

    def run(self) -> Any:
        try:
            self._setup_workflow()

            # NOTE: UI, add wf id
            # if(not self._validate_before_page_run()):
            if(not self._validate_before_run()):
                # NOTE: UI, add wf id
                # print("Multi-step Workflow terminated before page run")
                print("Multi-step Workflow terminated before run")
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
            print(f"MULTISTEP CONTRACT WORKFLOW EXCEPTION, {self.log_params}")
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

    # NOTE: UI
    # def _run_page(self, page, context) -> MultiStepResult:
    def _run(self) -> MultiStepResult:
        # NOTE: UI, add wf id
        processing_result = self._run_step()

        if processing_result.status == 'error':
            self.curr_step.status = WorkflowStepStatus.error
            self.curr_step.status_message = processing_result.error_msg
            self._save_to_db([self.curr_step])
        
        # Arbitrary wait to allow for enough time for WalletConnect relay to send our client the tx data
        # NOTE: UI, add wf id
        # page.wait_for_timeout(5000)
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

    # NOTE: UI
    # def _run_step(self, page, context) -> StepProcessingResult:
    def _run_step(self) -> StepProcessingResult:
        if not self.curr_step:
            return self._run_first_step()
        else:
            return self._run_next_step()

    # NOTE: UI
    # def _run_first_step(self, page, context) -> StepProcessingResult:
    def _run_first_step(self) -> StepProcessingResult:
        """Run first step, it is singled out as this is the only step that has no prior client response to process unlike other steps"""
        first_step = self.runnable_steps[0]

        # Save step to DB and set current step
        self._create_new_curr_step(first_step.type, 1, first_step.user_action_type, first_step.user_description)

        # return first_step.function(page, context)
        return first_step.function()


    def _run_next_step(self) -> StepProcessingResult:
        """Find the next step to run based on the current successful step from client response"""
        curr_runnable_step_index = [i for i,s in enumerate(self.runnable_steps) if s.type == self.curr_step.type][0]
        next_step_to_run_index = curr_runnable_step_index + 1
        next_step_to_run = self.runnable_steps[next_step_to_run_index]

        # Save step to DB and reset current step
        self._create_new_curr_step(next_step_to_run.type, next_step_to_run_index + 1, next_step_to_run.user_action_type, next_step_to_run.user_description)

        return next_step_to_run.function()

    def _setup_workflow(self):
        """
        This setup function does the following primary tasks:
        1. Create new workflow in DB if not already created
        2. User current step payload/feedback from client and save it to DB
        3. Set parsed_user_request to be used for logging
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
            # self.browser_storage_state = self.curr_step.step_state['browser_storage_state'] if  self.curr_step.step_state else None

            # Save current step status and user action data to DB that we receive from client
            self.curr_step.status = WorkflowStepStatus[self.curr_step_client_payload['status']]
            self.curr_step.status_message = self.curr_step_client_payload['statusMessage']
            self.curr_step.user_action_data = self.curr_step_client_payload['userActionData']
            self._save_to_db([self.curr_step])

        self.log_params = f"wf_type: {self.workflow_type}, chat_message_id: {self.chat_message_id}, wf_id: {self.workflow.id}, curr_step_type: {self.curr_step.type if self.curr_step else None}, wf_params: {self.workflow_params}"

    def _validate_before_run(self) -> bool:
        # Perform validation to check if we can continue with next step
        if self.curr_step:
            if self.curr_step.status != WorkflowStepStatus.success:
                print("Workflow step recorded an unsuccessful status from client")
                return False
            
            if self.curr_step.step_number == self.total_steps:
                print("Workflow has completed all steps")
                return False
        return True


    def _save_to_db(self, models: List[any]) -> None:
        db_session.add_all(models)
        db_session.commit()


    # NOTE: UI
    # def _preserve_browser_local_storage_item(self, context, key):
    #     storage_state = self._get_browser_cookies_and_storage(context)
    #     local_storage = storage_state['origins'][0]['localStorage']
    #     origin = storage_state['origins'][0]['origin']
    #     item_to_preserve = None
    #     for item in local_storage:
    #         if item['name'] == key:
    #             item_to_preserve = item
    #             break
    #     storage_state_to_save = {'origins': [{'origin': origin, 'localStorage': [item_to_preserve]}]}

    #     step_state = {
    #         "browser_storage_state": storage_state_to_save
    #     }

    #     self._update_step_state(step_state)

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

    # NOTE: UI
    # def _get_browser_cookies_and_storage(self, context) -> Dict:
    #     return context.storage_state()