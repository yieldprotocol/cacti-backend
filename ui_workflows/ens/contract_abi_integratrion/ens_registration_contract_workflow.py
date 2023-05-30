import uuid
import time
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from utils import hexify_token_amount
from ...base import BaseMultiStepContractWorkflow, WorkflowStepClientPayload, ContractStepProcessingResult, RunnableStep, WorkflowValidationError
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus, WorkflowStepUserActionType, ChatMessage, ChatSession, SystemConfig
)
from ..common import is_domain_registered, get_ens_registrar_controller_contract

ONE_MINUTE_REQUIRED_WAIT = 60
ONE_YEAR_DURATION = 365 * 24 * 60 * 60

class ENSRegistrationContractWorkflow(BaseMultiStepContractWorkflow):
    WORKFLOW_TYPE = 'register-ens-domain'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict, multistep_workflow: Optional[MultiStepWorkflow] = None, curr_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> None:
        self.domain = workflow_params['domain']
        self.name_label = self.domain.split('.')[0]

        step1 = RunnableStep("request_registration", WorkflowStepUserActionType.tx, f"ENS domain {self.domain} registration request. After confirming transaction, ENS will take ~1min to process next step", self.step_1_request_registration)
        step2 = RunnableStep("confirm_registration", WorkflowStepUserActionType.tx, f"ENS domain {self.domain} confirm registration", self.step_2_confirm_registration)

        steps = [step1, step2]

        final_step_type = "confirm_registration"
        
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, self.WORKFLOW_TYPE, multistep_workflow, workflow_params, curr_step_client_payload, steps, final_step_type)

    def _general_workflow_validation(self):
        # Check if domain is registered
        if (is_domain_registered(self.web3_provider, self.domain)):
            raise WorkflowValidationError(f"ENS name {self.domain} not available")


    def step_1_request_registration(self) -> ContractStepProcessingResult:
        """Step 1: Request registration"""

        # TODO: Should we require user to specify duration for the use of domain or default to 1 year?

        params = {
            'name': self.name_label,
            'owner': self.wallet_address,
            'duration': ONE_YEAR_DURATION,
            'secret': self.web3_provider.keccak(text=uuid.uuid4().hex),
            'resolver': '0x0000000000000000000000000000000000000000',
            'data': [],
            'reverseRecord': False,
            'ownerControlledFuses': 0
        }

        commitmentHash = get_ens_registrar_controller_contract().functions.makeCommitment(
            params['name'],
            params['owner'],
            params['duration'],
            params['secret'],
            params['resolver'],
            params['data'],
            params['reverseRecord'],
            params['ownerControlledFuses']
        ).call({})

        encoded_data = get_ens_registrar_controller_contract().encodeABI(fn_name='commit', args=[commitmentHash])

        tx = {
            'from': self.wallet_address,
            'to': get_ens_registrar_controller_contract().address, 
            'data': encoded_data,
        }

        # Store secret in step state to be used in next step
        self._update_step_state({
            'secret': params['secret'].hex(),
        })
        
        return ContractStepProcessingResult(status="success", tx=tx)
        
    
    def step_2_confirm_registration(self) -> ContractStepProcessingResult:
        """Step 2: Confirm registration"""

        # Get secret from previous step
        secret = self.prev_step.step_state['secret']

        # Wait for 1 min as per ENS docs - https://docs.ens.domains/contract-api-reference/.eth-permanent-registrar/controller
        time.sleep(ONE_MINUTE_REQUIRED_WAIT)

        (base_price, premium) = get_ens_registrar_controller_contract().functions.rentPrice(self.name_label, ONE_YEAR_DURATION).call({})

        # Add 10% to account for price fluctuation; the difference is refunded.
        adj_rent_price = (base_price + premium) * 1.1

        params = {
            'name': self.name_label,
            'owner': self.wallet_address,
            'duration': ONE_YEAR_DURATION,
            'secret': secret,
            'resolver': '0x0000000000000000000000000000000000000000',
            'data': [],
            'reverseRecord': False,
            'ownerControlledFuses': 0
        }

        encoded_data = get_ens_registrar_controller_contract().encodeABI(fn_name='register', args=[
            params['name'], params['owner'], params['duration'], params['secret'], params['resolver'], params['data'], params['reverseRecord'], params['ownerControlledFuses']
        ])

        tx = {
            'from': self.wallet_address,
            'to': get_ens_registrar_controller_contract().address, 
            'data': encoded_data,
            'value': hex(int(adj_rent_price)),
        }

        return ContractStepProcessingResult(status='success', tx=tx)