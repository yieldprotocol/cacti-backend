import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from database.models import db_session, WorkflowStep, WorkflowStepStatus, MultiStepWorkflow

from .common import WorkflowStepClientPayload, RunnableStep, StepProcessingResult, MultiStepResult, WorkflowValidationError
from .base_ui_workflow import BaseUIWorkflow
from .base_multi_step_mixin import BaseMultiStepMixin, WorkflowApproach

class BaseMultiStepUIWorkflow(BaseUIWorkflow, BaseMultiStepMixin):
    """Base class for multi-step UI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, multistep_workflow: Optional[MultiStepWorkflow], workflow_params: Dict, curr_step_client_payload: Optional[WorkflowStepClientPayload], runnable_steps: List[RunnableStep], final_step_type: str) -> None:
        BaseUIWorkflow.__init__(self, wallet_chain_id, wallet_address, chat_message_id, workflow_type, workflow_params)
        BaseMultiStepMixin.__init__(self, WorkflowApproach.UI, self.wallet_chain_id, self.wallet_address, self.chat_message_id, self.workflow_type, multistep_workflow, self.workflow_params, curr_step_client_payload, runnable_steps, final_step_type)

    def run(self) -> MultiStepResult:
        return BaseMultiStepMixin.run(self)

    def _run_page(self, page, browser_context) -> MultiStepResult:
        return BaseMultiStepMixin._run(self, page, browser_context)

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

    def _get_browser_cookies_and_storage(self, browser_context) -> Dict:
        return browser_context.storage_state()