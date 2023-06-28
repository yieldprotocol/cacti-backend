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
from ..common import SAVINGS_DAI_ADDRESS, get_savings_dai_address_contract, savings_dai_check_for_error_and_compute_result

class SavingsDaiRedeemContractWorkflow(BaseMultiStepContractWorkflow):
    WORKFLOW_TYPE = 'savings-dai-redeem'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        serlf.token = "SavingsDAI"
        self.amount = workflow_params["amount"]

        # The only token that can be redeemed is SavingsDAI, you have to handle approval before final confirmation
        initiate_erc20_approval_step = RunnableStep("initiate_ERC20_approval", WorkflowStepUserActionType.tx, f"Approve redemption of {self.amount} {self.token} on SavingsDAI", self.initiate_erc20_approval_step)
        confirm_erc4626_redeem_step = RunnableStep("confirm_ERC4626_redeem", WorkflowStepUserActionType.tx, f"Confirm redemption of {self.amount} {self.token} on SavingsDAI", self.confirm_erc20_deposit_step)
        steps = [initiate_erc20_approval_step, confirm_erc4626_redeem_step]

        final_step_type = "confirm_erc4626_redeem"
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, self.WORKFLOW_TYPE, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def _general_workflow_validation(self):
        if (get_token_balance(self.web3_provider, self.wallet_chain_id, self.token, self.wallet_address) < parse_token_amount(self.wallet_chain_id, self.token, self.amount)):
            raise WorkflowValidationError(f"Insufficient {self.token} balance in wallet")


    def initiate_ERC20_approval_step(self):
        """Initiate approval of ERC20 token to be taken by SavingsDAI"""
        return self._initiate_ERC20_approval(SAVINGS_DAI_ADDRESS, self.token, self.amount, 'confirm_ERC20_approval')

    def confirm_ERC4626_redeem_step(self, extra_params=None) -> ContractStepProcessingResult:
        """Confirm redemption of SavingsDAI"""

        asset = get_token_address(self.wallet_chain_id, self.token)
        amount = parse_token_amount(self.wallet_chain_id, self.token, self.amount)
        on_behalf_of = self.wallet_address
        referral_code = 0
        encoded_data = get_savings_dai_address_contract().encodeABI(fn_name='redeem', args=[amount, self.wallet_address])
        tx = {
            'from': self.wallet_address, 
            'to': SAVINGS_DAI_ADDRESS, 
            'data': encoded_data,
        }
        
        return savings_dai_check_for_error_and_compute_result(self, tx)
