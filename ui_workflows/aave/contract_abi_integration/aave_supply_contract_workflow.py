import re
from logging import basicConfig, INFO
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import env
from utils import TENDERLY_FORK_URL, w3, ERC20_ABI, get_token_balance, estimate_gas, parse_token_amount, hexify_token_amount
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)
from ...base import BaseMultiStepContractWorkflow, WorkflowStepClientPayload, RunnableStep, WorkflowValidationError, ContractStepProcessingResult
from ..common import AAVE_SUPPORTED_TOKENS, AAVE_POOL_V3_PROXY_ADDRESS, AAVE_WRAPPED_TOKEN_GATEWAY, aave_pool_v3_address, aave_wrapped_token_gateway

class AaveSupplyContractWorkflow(BaseMultiStepContractWorkflow):
    """
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
        
        if (get_token_balance(self.token, self.wallet_address) < parse_token_amount(self.wallet_chain_id, self.token, self.amount)):
            raise WorkflowValidationError(f"Insufficient {self.token} balance in wallet")


    def confirm_ETH_supply_step(self) -> ContractStepProcessingResult:
        """Confirm supply of ETH/ERC20 token"""

        tx_input = aave_wrapped_token_gateway.encodeABI(fn_name='depositETH', args=[AAVE_POOL_V3_PROXY_ADDRESS, self.wallet_address, 0])

        tx = {
            'from': self.wallet_address, 
            'to': AAVE_WRAPPED_TOKEN_GATEWAY, 
            'data': tx_input,
            'value': hexify_token_amount(self.wallet_chain_id, self.token, self.amount),
        }
        
        tx['gas'] = estimate_gas(tx)

        return ContractStepProcessingResult(status="success", tx=tx)

    # def initiate_ERC20_approval_step(self):
    #     """
    #     - refactor StepResult to include tx hash
    #     - check if erc20 already approved, if approved replace with next step
    #     """
    #     pass

    # def confirm_ERC20_supply_step(self, extra_params=None) -> StepProcessingResult:
    #     """Confirm supply of ETH/ERC20 token"""
    #     pass