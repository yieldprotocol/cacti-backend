import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

from utils import estimate_gas
from database.models import db_session, WorkflowStep, WorkflowStepStatus, MultiStepWorkflow

from .common import WorkflowStepClientPayload, RunnableStep, ContractStepProcessingResult, MultiStepResult, WorkflowValidationError, compute_abi_abspath
from .base_contract_workflow import BaseContractWorkflow
from .base_multi_step_mixin import BaseMultiStepMixin, WorkflowApproach

class BaseMultiStepContractWorkflow(BaseContractWorkflow, BaseMultiStepMixin):
    """Base class for multi-step contract ABI workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, multistep_workflow: Optional[MultiStepWorkflow], workflow_params: Dict, curr_step_client_payload: Optional[WorkflowStepClientPayload], runnable_steps: List[RunnableStep], final_step_type) -> None:
        BaseContractWorkflow.__init__(self, wallet_chain_id, wallet_address, chat_message_id, workflow_type, workflow_params)
        BaseMultiStepMixin.__init__(self, WorkflowApproach.CONTRACT, self.wallet_chain_id, self.wallet_address, self.chat_message_id, self.workflow_type, multistep_workflow, self.workflow_params, curr_step_client_payload, runnable_steps, final_step_type)

    def run(self) -> MultiStepResult:
        return BaseMultiStepMixin.run(self)

    def _run(self) -> MultiStepResult:
        return BaseMultiStepMixin._run(self)