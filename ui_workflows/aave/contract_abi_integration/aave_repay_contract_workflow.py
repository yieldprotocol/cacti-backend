from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

import web3

from utils import get_token_balance, parse_token_amount, hexify_token_amount, estimate_gas, get_token_address, generate_erc20_approve_encoded_data, has_sufficient_erc20_allowance
from ...base import RunnableStep, WorkflowStepClientPayload, BaseMultiStepContractWorkflow, WorkflowValidationError, ContractStepProcessingResult, tenderly_simulate_tx
from database.models import (
    MultiStepWorkflow, WorkflowStepUserActionType
)
from ..common import AAVE_SUPPORTED_TOKENS, AAVE_POOL_V3_PROXY_ADDRESS, AAVE_WRAPPED_TOKEN_GATEWAY, AAVE_VARIABLE_DEBT_TOKEN_ADDRESS, get_aave_wrapped_token_gateway_contract, get_aave_variable_debt_token_contract, get_aave_pool_v3_address_contract, common_aave_validation

class AaveRepayContractWorkflow(BaseMultiStepContractWorkflow):        
    WORKFLOW_TYPE = 'aave-repay'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params["token"]
        self.amount = workflow_params["amount"]

        if self.token == "ETH":
            confirm_ETH_repay_step = RunnableStep("confirm_ETH_repay", WorkflowStepUserActionType.tx, f"Confirm repay of {self.amount} ETH on Aave", self.confirm_ETH_repay)
            steps = [confirm_ETH_repay_step]
            
            final_step_type = confirm_ETH_repay_step.type
        else:
            initiate_ERC20_approval_step = RunnableStep("initiate_ERC20_approve", WorkflowStepUserActionType.tx, f"Approve repay of {self.amount} {self.token} on Aave", self.initiate_ERC20_approval)
            confirm_ERC20_repay_step = RunnableStep("confirm_ERC20_repay", WorkflowStepUserActionType.tx, f"Confirm repay of {self.amount} {self.token} on Aave", self.confirm_ERC20_repay)
            steps = [initiate_ERC20_approval_step, confirm_ERC20_repay_step]
            final_step_type = confirm_ERC20_repay_step.type

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, self.WORKFLOW_TYPE, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def _general_workflow_validation(self):
        common_aave_validation(self.token)

    def confirm_ETH_repay(self):
        pool_address = AAVE_POOL_V3_PROXY_ADDRESS
        amount = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        interest_rate_mode = 2
        on_behalf_of = self.wallet_address
        encoded_data = get_aave_wrapped_token_gateway_contract().encodeABI(fn_name='repayETH', args=[pool_address, amount, interest_rate_mode, on_behalf_of])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_WRAPPED_TOKEN_GATEWAY, 
            'data': encoded_data,
            'value': hexify_token_amount(self.wallet_chain_id, self.token, self.amount)
        }
        
        return ContractStepProcessingResult(status="success", tx=tx)

    def initiate_ERC20_approval(self):
        return self._initiate_ERC20_approval(AAVE_POOL_V3_PROXY_ADDRESS, self.token, self.amount, 'confirm_ERC20_repay')

    def confirm_ERC20_repay(self):        
        asset_address = get_token_address(self.wallet_chain_id, self.token)
        amount = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        interest_rate_mode = 2
        on_behalf_of = self.wallet_address

        encoded_data = get_aave_pool_v3_address_contract().encodeABI(fn_name='repay', args=[asset_address, amount, interest_rate_mode, on_behalf_of])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_POOL_V3_PROXY_ADDRESS, 
            'data': encoded_data,
        }
        
        return ContractStepProcessingResult(status="success", tx=tx)