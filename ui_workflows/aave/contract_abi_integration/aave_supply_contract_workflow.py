import re
from logging import basicConfig, INFO
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import env
from utils import get_token_balance, estimate_gas, parse_token_amount, hexify_token_amount, has_sufficient_erc20_allowance, generate_erc20_approve_encoded_data, get_token_address
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStepUserActionType
)
from ...base import BaseMultiStepContractWorkflow, WorkflowStepClientPayload, RunnableStep, WorkflowValidationError, ContractStepProcessingResult
from ..common import AAVE_SUPPORTED_TOKENS, AAVE_POOL_V3_PROXY_ADDRESS, AAVE_WRAPPED_TOKEN_GATEWAY, get_aave_pool_v3_address_contract, get_aave_wrapped_token_gateway_contract

class AaveSupplyContractWorkflow(BaseMultiStepContractWorkflow):
    """
    NOTE: Refer to the docstring in ../ui_integration/aave_supply_ui_workflow.py (AaveSupplyUIWorkflow) to get more info on the various scenarios to handle for Aave supply
    """
    WORKFLOW_TYPE = 'aave-supply'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.token = workflow_params["token"]
        self.amount = workflow_params["amount"]

        # Only one step for ETH as it doesn't require an approval step unlike ERC20 tokens
        if self.token == "ETH":
            confirm_ETH_supply_step = RunnableStep("confirm_ETH_supply", WorkflowStepUserActionType.tx, f"Confirm supply of {self.amount} ETH on Aave", self.confirm_ETH_supply_step)
            steps = [confirm_ETH_supply_step]
            final_step_type = "confirm_ETH_supply"
        else:
            # For ERC20 you have to handle approval before final confirmation
            initiate_ERC20_approval_step = RunnableStep("initiate_ERC20_approval", WorkflowStepUserActionType.tx, f"Approve supply of {self.amount} {self.token} on Aave", self.initiate_ERC20_approval_step)
            confirm_ERC20_supply_step = RunnableStep("confirm_ERC20_supply", WorkflowStepUserActionType.tx, f"Confirm supply of {self.amount} {self.token} on Aave", self.confirm_ERC20_supply_step)
            steps = [initiate_ERC20_approval_step, confirm_ERC20_supply_step]

            final_step_type = "confirm_ERC20_supply"
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, self.WORKFLOW_TYPE, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def _pre_workflow_validation(self):
        if (self.token not in AAVE_SUPPORTED_TOKENS):
            raise WorkflowValidationError(f"Token {self.token} not supported by Aave")
        
        if (get_token_balance(self.web3_provider, self.wallet_chain_id, self.token, self.wallet_address) < parse_token_amount(self.wallet_chain_id, self.token, self.amount)):
            raise WorkflowValidationError(f"Insufficient {self.token} balance in wallet")


    def confirm_ETH_supply_step(self) -> ContractStepProcessingResult:
        """Confirm supply of ETH/ERC20 token"""

        pool_address = AAVE_POOL_V3_PROXY_ADDRESS
        on_behalf_of = self.wallet_address
        referral_code = 0
        encoded_data = get_aave_wrapped_token_gateway_contract().encodeABI(fn_name='depositETH', args=[pool_address, on_behalf_of, referral_code])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_WRAPPED_TOKEN_GATEWAY, 
            'data': encoded_data,
            'value': hexify_token_amount(self.wallet_chain_id, self.token, self.amount),
        }
        
        return ContractStepProcessingResult(status="success", tx=tx)

    def initiate_ERC20_approval_step(self):
        """Initiate approval of ERC20 token to be spent by Aave"""

        if (has_sufficient_erc20_allowance(self.web3_provider, self.wallet_chain_id, self.token, self.wallet_address, AAVE_POOL_V3_PROXY_ADDRESS, self.amount)):
            return ContractStepProcessingResult(status="replace", replace_with_step_type="confirm_ERC20_supply")

        spender = AAVE_POOL_V3_PROXY_ADDRESS
        value = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        encoded_data = generate_erc20_approve_encoded_data(self.web3_provider, self.wallet_chain_id, self.token, spender, value)
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
        encoded_data = get_aave_pool_v3_address_contract().encodeABI(fn_name='supply', args=[asset, amount, on_behalf_of, referral_code])
        tx = {
            'from': self.wallet_address, 
            'to': AAVE_POOL_V3_PROXY_ADDRESS, 
            'data': encoded_data,
        }
        
        return ContractStepProcessingResult(status="success", tx=tx)
