import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

from utils import parse_token_amount, generate_erc20_approve_encoded_data, has_sufficient_erc20_allowance, get_token_address
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
    
    def _initiate_ERC20_approval(self, spender, token, amount, replace_with_step_type):
        if (has_sufficient_erc20_allowance(self.web3_provider, self.wallet_chain_id, token, self.wallet_address, spender, amount)):
            return ContractStepProcessingResult(status="replace", replace_with_step_type=replace_with_step_type)

        value = parse_token_amount(self.wallet_chain_id, token, amount)
        encoded_data = generate_erc20_approve_encoded_data(self.web3_provider, self.wallet_chain_id, token, spender, value)
        tx = {
            'from': self.wallet_address, 
            'to': get_token_address(self.wallet_chain_id, token), 
            'data': encoded_data,
        }
        return ContractStepProcessingResult(status="success", tx=tx) 