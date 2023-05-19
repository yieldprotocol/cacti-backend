import re
from logging import basicConfig, INFO
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import env
from utils import TENDERLY_FORK_URL, w3, ERC20_ABI, get_token_balance, estimate_gas, parse_token_amount, hexify_token_amount, has_sufficient_erc20_allowance, generate_erc20_approve_encoded_data, get_token_address
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStepUserActionType
)
from ...base import BaseMultiStepContractWorkflow, WorkflowStepClientPayload, RunnableStep, WorkflowValidationError, ContractStepProcessingResult
from ..common import AAVE_SUPPORTED_TOKENS, AAVE_POOL_V3_PROXY_ADDRESS, AAVE_WRAPPED_TOKEN_GATEWAY, aave_pool_v3_address_contract, aave_wrapped_token_gateway_contract

class AaveBorrowContractWorkflow(BaseMultiStepContractWorkflow):
    """
    NOTE: Refer to the docstring in ../ui_integration/aave_borrow_ui_workflow.py (AaveBorrowUIWorkflow) to get more info on the various scenarios to handle for Aave borrow
    """
    WORKFLOW_TYPE = 'aave-borrow'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params["token"]
        self.amount = workflow_params["amount"]

        if self.token == "ETH":
            check_ETH_liquidation_risk_step = RunnableStep("check_ETH_liquidation_risk", WorkflowStepUserActionType.acknowledge, f"Acknowledge liquidation risk due to high borrow amount of {self.amount} ETH on Aave", self.check_ETH_liquidation_risk)
            initiate_ETH_approval_step = RunnableStep("initiate_ETH_approval", WorkflowStepUserActionType.tx, f"Approve borrow of {self.amount} ETH on Aave", self.initiate_ETH_approval)
            confirm_ETH_borrow_step = RunnableStep("confirm_ETH_borrow", WorkflowStepUserActionType.tx, f"Confirm borrow of {self.amount} ETH on Aave", self.confirm_ETH_borrow)
            steps = [check_ETH_liquidation_risk_step, initiate_ETH_approval_step, confirm_ETH_borrow_step]
            
            final_step_type = "confirm_ETH_borrow"
        else:
            check_ERC20_liquidation_risk = RunnableStep("check_ERC20_liquidation_risk", WorkflowStepUserActionType.acknowledge, f"Acknowledge liquidation risk due to high borrow amount of {self.amount} {self.token} on Aave", self.check_ERC20_liquidation_risk)
            confirm_ERC20_borrow_step = RunnableStep("confirm_ERC20_borrow", WorkflowStepUserActionType.tx, f"Confirm borrow of {self.amount} {self.token} from Aave", self.confirm_ERC20_borrow)
            steps = [check_ERC20_liquidation_risk, confirm_ERC20_borrow_step]
            final_step_type = "confirm_ERC20_borrow"
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, self.WORKFLOW_TYPE, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def _pre_workflow_validation(self):
        if (self.token not in AAVE_SUPPORTED_TOKENS):
            raise WorkflowValidationError(f"Token {self.token} not supported by Aave")
        
        if (get_token_balance(self.wallet_chain_id, self.token, self.wallet_address) < parse_token_amount(self.wallet_chain_id, self.token, self.amount)):
            raise WorkflowValidationError(f"Insufficient {self.token} balance in wallet")


    def confirm_ETH_supply_step(self) -> ContractStepProcessingResult:
        """Confirm supply of ETH/ERC20 token"""

        pool_address = AAVE_POOL_V3_PROXY_ADDRESS
        on_behalf_of = self.wallet_address
        referral_code = 0
        encoded_data = aave_wrapped_token_gateway_contract.encodeABI(fn_name='depositETH', args=[pool_address, on_behalf_of, referral_code])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_WRAPPED_TOKEN_GATEWAY, 
            'data': encoded_data,
            'value': hexify_token_amount(self.wallet_chain_id, self.token, self.amount),
        }
        
        return ContractStepProcessingResult(status="success", tx=tx)

    def initiate_ERC20_approval_step(self):
        """Initiate approval of ERC20 token to be spent by Aave"""

        if (has_sufficient_erc20_allowance(self.wallet_chain_id, self.token, self.wallet_address, AAVE_POOL_V3_PROXY_ADDRESS, self.amount)):
            return ContractStepProcessingResult(status="replace", replace_with_step_type="confirm_ERC20_supply")

        spender = AAVE_POOL_V3_PROXY_ADDRESS
        value = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        encoded_data = generate_erc20_approve_encoded_data(self.wallet_chain_id, self.token, spender, value)
        tx = {
            'from': self.wallet_address, 
            'to': get_token_address(self.wallet_chain_id, self.token), 
            'data': encoded_data,
        }
        return ContractStepProcessingResult(status="success", tx=tx)
        

    def confirm_ERC20_supply_step(self, extra_params=None) -> ContractStepProcessingResult:
        """Confirm supply of ERC20 token"""

        asset = get_token_address(self.wallet_chain_id, self.token)
        amount = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        on_behalf_of = self.wallet_address
        referral_code = 0
        encoded_data = aave_pool_v3_address_contract.encodeABI(fn_name='supply', args=[asset, amount, on_behalf_of, referral_code])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_POOL_V3_PROXY_ADDRESS, 
            'data': encoded_data,
        }
        
        return ContractStepProcessingResult(status="success", tx=tx)
