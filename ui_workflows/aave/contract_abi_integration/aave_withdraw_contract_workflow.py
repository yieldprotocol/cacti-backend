from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

import web3

from utils import get_token_balance, parse_token_amount, hexify_token_amount, estimate_gas, get_token_address, generate_erc20_approve_encoded_data, has_sufficient_erc20_allowance
from ...base import RunnableStep, WorkflowStepClientPayload, BaseMultiStepContractWorkflow, WorkflowValidationError, ContractStepProcessingResult
from database.models import (
    MultiStepWorkflow, WorkflowStepUserActionType
)
from ..common import AAVE_POOL_V3_PROXY_ADDRESS, AAVE_WRAPPED_TOKEN_GATEWAY, get_aave_wrapped_token_gateway_contract, get_aave_pool_v3_address_contract, common_aave_validation, get_aave_atoken_contract, aave_check_for_error_and_compute_result

class AaveWithdrawContractWorkflow(BaseMultiStepContractWorkflow):        
    WORKFLOW_TYPE = 'aave-withdraw'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params["token"]
        self.amount = workflow_params["amount"]

        if self.token == "ETH":
            initiate_ETH_approval_step = RunnableStep("initiate_ETH_approval", WorkflowStepUserActionType.tx, f"Approve withdraw of {self.amount} ETH on Aave", self.initiate_ETH_approval)
            confirm_ETH_withdraw_step = RunnableStep("confirm_ETH_withdraw", WorkflowStepUserActionType.tx, f"Confirm withdraw of {self.amount} ETH on Aave", self.confirm_ETH_withdraw)
            steps = [initiate_ETH_approval_step, confirm_ETH_withdraw_step]
            
            final_step_type = confirm_ETH_withdraw_step.type
        else:
            confirm_ERC20_withdraw_step = RunnableStep("confirm_ERC20_withdraw", WorkflowStepUserActionType.tx, f"Confirm withdraw of {self.amount} {self.token} on Aave", self.confirm_ERC20_withdraw)
            steps = [confirm_ERC20_withdraw_step]
            final_step_type = confirm_ERC20_withdraw_step.type

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, self.WORKFLOW_TYPE, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def _general_workflow_validation(self):
        common_aave_validation(self.token)

    def initiate_ETH_approval(self): 
        owner = self.wallet_address
        spender = AAVE_WRAPPED_TOKEN_GATEWAY

        allowance = get_aave_atoken_contract().functions.allowance(owner, spender).call()

        if parse_token_amount(self.wallet_chain_id, self.token, self.amount) <= allowance:
            return ContractStepProcessingResult(status="replace", replace_with_step_type="confirm_ETH_withdraw")
    
        amount = int(web3.constants.MAX_INT, 16)

        encoded_data = get_aave_atoken_contract().encodeABI(fn_name='approve', args=[spender, amount])
        tx = {
            'from': self.wallet_address, 
            'to': get_aave_atoken_contract().address, 
            'data': encoded_data,
        }
        
        return ContractStepProcessingResult(status="success", tx=tx)

    def confirm_ETH_withdraw(self):
        pool_address = AAVE_POOL_V3_PROXY_ADDRESS
        amount = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        to_address = self.wallet_address
        encoded_data = get_aave_wrapped_token_gateway_contract().encodeABI(fn_name='withdrawETH', args=[pool_address, amount, to_address])
        tx = {
            'from': self.wallet_address, 
            'to': get_aave_wrapped_token_gateway_contract().address, 
            'data': encoded_data,
        }
        
        return aave_check_for_error_and_compute_result(self, tx)

    def confirm_ERC20_withdraw(self): 
        asset_address = get_token_address(self.wallet_chain_id, self.token)
        amount = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        to_address = self.wallet_address
        encoded_data = get_aave_pool_v3_address_contract().encodeABI(fn_name='withdraw', args=[asset_address, amount, to_address])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_POOL_V3_PROXY_ADDRESS, 
            'data': encoded_data,
        }
        
        return aave_check_for_error_and_compute_result(self, tx)