from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

import web3

from utils import get_token_balance, parse_token_amount, hexify_token_amount, estimate_gas, get_token_address
from ...base import RunnableStep, WorkflowStepClientPayload, BaseMultiStepContractWorkflow, WorkflowValidationError, ContractStepProcessingResult, tenderly_simulate_tx
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)
from ..common import AAVE_SUPPORTED_TOKENS, AAVE_POOL_V3_PROXY_ADDRESS, AAVE_WRAPPED_TOKEN_GATEWAY, AAVE_VARIABLE_DEBT_TOKEN_ADDRESS, get_aave_wrapped_token_gateway_contract, get_aave_variable_debt_token_contract, get_aave_pool_v3_address_contract

class AaveBorrowContractWorkflow(BaseMultiStepContractWorkflow):
    """
    NOTE: Refer to the docstring in ../ui_integration/aave_borrow_ui_workflow.py (AaveBorrowUIWorkflow) to get more info on the various scenarios to handle for Aave borrow
    """
        
    WORKFLOW_TYPE = 'aave-borrow'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params["token"]
        self.amount = workflow_params["amount"]

        if self.token == "ETH":
            # check_ETH_liquidation_risk_step = RunnableStep("check_ETH_liquidation_risk", WorkflowStepUserActionType.acknowledge, f"Acknowledge liquidation risk due to high borrow amount of {self.amount} ETH on Aave", self.check_ETH_liquidation_risk)
            initiate_ETH_approval_step = RunnableStep("initiate_ETH_approval", WorkflowStepUserActionType.tx, f"Approve borrow of {self.amount} ETH on Aave", self.initiate_ETH_approval)
            confirm_ETH_borrow_step = RunnableStep("confirm_ETH_borrow", WorkflowStepUserActionType.tx, f"Confirm borrow of {self.amount} ETH on Aave", self.confirm_ETH_borrow)
            steps = [initiate_ETH_approval_step, confirm_ETH_borrow_step]
            
            final_step_type = "confirm_ETH_borrow"
        else:
            # check_ERC20_liquidation_risk = RunnableStep("check_ERC20_liquidation_risk", WorkflowStepUserActionType.acknowledge, f"Acknowledge liquidation risk due to high borrow amount of {self.amount} {self.token} on Aave", self.check_ERC20_liquidation_risk)
            confirm_ERC20_borrow_step = RunnableStep("confirm_ERC20_borrow", WorkflowStepUserActionType.tx, f"Confirm borrow of {self.amount} {self.token} on Aave", self.confirm_ERC20_borrow)
            steps = [confirm_ERC20_borrow_step]
            final_step_type = "confirm_ERC20_borrow"

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, self.WORKFLOW_TYPE, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def _general_workflow_validation(self):
        if (self.token not in AAVE_SUPPORTED_TOKENS):
            raise WorkflowValidationError(f"Token {self.token} not supported by Aave")

        # TODO: add a check to verify that the user has deposited collateral


    def check_ETH_liquidation_risk(self):
        # TODO: add a check to get the health factor and ensure that it is not too high
        pass
     
    def initiate_ETH_approval(self):
        """Initiate approval for ETH token"""

        from_address = self.wallet_address
        to_address = AAVE_WRAPPED_TOKEN_GATEWAY

        borrow_allowance = get_aave_variable_debt_token_contract().functions.borrowAllowance(from_address, to_address).call()

        if parse_token_amount(self.wallet_chain_id, self.token, self.amount) <= borrow_allowance:
            return ContractStepProcessingResult(status="replace", replace_with_step_type="confirm_ETH_borrow")

        delegatee = AAVE_WRAPPED_TOKEN_GATEWAY
        amount = int(web3.constants.MAX_INT, 16)
        encoded_data = get_aave_variable_debt_token_contract().encodeABI(fn_name='approveDelegation', args=[delegatee, amount])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_VARIABLE_DEBT_TOKEN_ADDRESS, 
            'data': encoded_data,
        }

        return ContractStepProcessingResult(status="success", tx=tx)  

    def confirm_ETH_borrow(self, extra_params=None):
        pool_address = AAVE_POOL_V3_PROXY_ADDRESS
        amount = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        interest_rate_mode = 2 # Variable
        referral_code = 0
        encoded_data = get_aave_wrapped_token_gateway_contract().encodeABI(fn_name='borrowETH', args=[pool_address, amount, interest_rate_mode, referral_code])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_WRAPPED_TOKEN_GATEWAY, 
            'data': encoded_data,
        }
        
        return ContractStepProcessingResult(status="success", tx=tx)

    def check_ERC20_liquidation_risk(self, page, browser_context):   
        pass
        
    def confirm_ERC20_borrow(self):
        asset_address = get_token_address(self.wallet_chain_id, self.token)
        amount = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        interest_rate_mode = 2 # Variable
        referral_code = 0
        on_behalf_of = self.wallet_address

        encoded_data = get_aave_pool_v3_address_contract().encodeABI(fn_name='borrow', args=[asset_address, amount, interest_rate_mode, referral_code, on_behalf_of])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_POOL_V3_PROXY_ADDRESS, 
            'data': encoded_data,
        }
        
        return ContractStepProcessingResult(status="success", tx=tx)