import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from database.models import db_session, WorkflowStep, WorkflowStepStatus, MultiStepWorkflow

from .common import WorkflowStepClientPayload, RunnableStep, StepProcessingResult, MultiStepResult, WorkflowValidationError
from .base_ui_workflow import BaseUIWorkflow

class BaseMultiStepUIWorkflow(BaseUIWorkflow):
    """Base class for multi-step UI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, multistep_workflow: Optional[MultiStepWorkflow], worfklow_params: Dict, curr_step_client_payload: Optional[WorkflowStepClientPayload], runnable_steps: List[RunnableStep], final_step_type: str) -> None:

        self.chat_message_id = chat_message_id
        self.multistep_workflow = multistep_workflow
        self.multistep_workflow_id = multistep_workflow.id if multistep_workflow else str(uuid.uuid4()) # When this workflow is initiated for the first time, there will not be a multistep workflow record in DB yet so we initialize the ID here with a random UUID which will be stored later in the DB when the workflow is saved
        self.workflow_type = workflow_type
        self.workflow_params = worfklow_params
        self.runnable_steps = runnable_steps
        self.curr_step_client_payload = curr_step_client_payload
        self.final_step_type = final_step_type
        
        self.curr_step: Optional[WorkflowStep] = None
        self.curr_step_description = None
        self.prev_step: Optional[WorkflowStep] = None

        browser_storage_state = None

        super().__init__(wallet_chain_id, wallet_address, browser_storage_state)

    def run(self) -> MultiStepResult:
        start_log_params = f"{self.workflow_type}, chat_message_id: {self.chat_message_id}, multistep_wf_id: {self.multistep_workflow_id}, curr_step_id: {self.curr_step_client_payload['id'] if self.curr_step_client_payload else None}, curr_step_type: {self.curr_step_client_payload['type'] if self.curr_step_client_payload else self.runnable_steps[0].type}, wf_params: {self.workflow_params}"
        print(f"Multi-step UI workflow started, wf_type: {start_log_params}")
        try:
            self._setup_workflow()

            if(self._check_should_terminate_run()):
                print(f"Multi-step Workflow terminated before page run, {start_log_params}")
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
            
            return super().run()
        except WorkflowValidationError as e:
            print(f"MULTISTEP UI WORKFLOW VALIDATION ERROR, {start_log_params}")
            traceback.print_exc()
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
                error_msg=e.args[0],
                description=self.curr_step_description
            )
        except Exception:
            print(f"MULTISTEP UI WORKFLOW EXCEPTION, {start_log_params}")
            traceback.print_exc()
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
                error_msg="Unexpected error. Check with support.",
                description=self.curr_step_description
            )
        finally:
            self.stop_listener()
            end_log_params = f"wf_type: {self.workflow_type}, chat_message_id: {self.chat_message_id}, multistep_wf_id: {self.multistep_workflow_id}, curr_step_id: {self.curr_step.id}, curr_step_type: {self.curr_step.type}"
            print(f"Multi-step UI workflow ended, {end_log_params}")

    def _run_page(self, page, browser_context) -> MultiStepResult:
        processing_result = self._run_step(page, browser_context)

        if processing_result.status == 'error':
            self.curr_step.status = WorkflowStepStatus.error
            self.curr_step.status_message = processing_result.error_msg
            self._save_to_db([self.curr_step])
        
        # Arbitrary wait to allow for enough time for WalletConnect relay to send our client the tx data
        page.wait_for_timeout(5000)

        # Stop WC listener thread and extract tx data if any
        tx = self.stop_listener()

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

    def _run_step(self, page, browser_context, replacement_step_type=None, extra_params=None) -> StepProcessingResult:
        if replacement_step_type:
            result = self._handle_step_replace(page, browser_context, replacement_step_type, extra_params)
        elif not self.curr_step:
            result = self._run_first_step(page, browser_context)
        else:
            self.prev_step = self.curr_step
            result = self._run_next_step(page, browser_context)

        if result.status == 'replace':
            return self._run_step(page, browser_context, replacement_step_type=result.replace_with_step_type, extra_params=result.replace_extra_params)
        else:
            return result

    def _run_first_step(self, page, browser_context) -> StepProcessingResult:
        """Run first step, it is singled out as this is the only step that has no prior client response to process unlike other steps"""
        first_step = self.runnable_steps[0]

        # Save step to DB and set current step
        self._create_new_curr_step(first_step.type, 1, first_step.user_action_type, first_step.user_description)

        return first_step.function(page, browser_context)

    def _run_next_step(self, page, browser_context) -> StepProcessingResult:
        """Find the next step to run based on the current successful step from client response"""

        curr_runnable_step_index = self._find_runnable_step_index_by_step_type(self.curr_step.type)
        next_step_to_run_index = curr_runnable_step_index + 1
        next_step_to_run = self.runnable_steps[next_step_to_run_index]

        # Save step to DB and reset current step
        self._create_new_curr_step(next_step_to_run.type, next_step_to_run_index + 1, next_step_to_run.user_action_type, next_step_to_run.user_description)

        return next_step_to_run.function(page, browser_context)

    def _handle_step_replace(self, page, browser_context, replace_with_step_type: str, replace_extra_params: Dict) -> StepProcessingResult:
        if not self.final_step_type:
            raise WorkflowValidationError("Variable self.final_step_type must be set for workflow with replace condition")

        print(f"Workflow step replacement being processed, wf_type: {self.workflow_type}, multistep_wf_id: {self.multistep_workflow_id}, curr_step_id: {self.curr_step.id}, from_step_type: {self.curr_step.type}, to_step_type: {replace_with_step_type}")

        runnable_step_index = self._find_runnable_step_index_by_step_type(replace_with_step_type)
        runnable_step = self.runnable_steps[runnable_step_index]

        self.curr_step.type = runnable_step.type
        self.curr_step.user_action_type = runnable_step.user_action_type
        self._save_to_db([self.curr_step])

        self.curr_step_description = runnable_step.user_description

        return runnable_step.function(page, browser_context, replace_extra_params)
        
    def _find_runnable_step_index_by_step_type(self, step_type) -> int:
        return [i for i,s in enumerate(self.runnable_steps) if s.type == step_type][0]

    def _setup_workflow(self):
        """
        This setup function does the following primary tasks:
        1. Create new workflow in DB if not already created
        2. Use current step payload/feedback from client to get the step's browser storage state so that it can be injected into the browser browser_context to be used in next step
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

            self.browser_storage_state = self.curr_step.step_state['browser_storage_state'] if  self.curr_step.step_state else None

            # Save current step status and user action data to DB that we receive from client
            self.curr_step.status = WorkflowStepStatus[self.curr_step_client_payload['status']]
            self.curr_step.status_message = self.curr_step_client_payload['statusMessage']
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
        return self.curr_step.type == self.final_step_type

    def _save_to_db(self, models: List[any]) -> None:
        db_session.add_all(models)
        db_session.commit()

    def _preserve_browser_local_storage_item(self, browser_context, key):
        storage_state = self._get_browser_cookies_and_storage(browser_context)
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

    def _get_browser_cookies_and_storage(self, browser_context) -> Dict:
        return browser_context.storage_state()