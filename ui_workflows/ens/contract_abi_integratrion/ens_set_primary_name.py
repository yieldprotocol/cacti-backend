import re
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from web3 import Web3

from ...base import Result, BaseSingleStepContractWorkflow, WorkflowValidationError
from ..common import get_ens_reverse_registrar_contract, ens_update_common_pre_workflow_validation


class ENSSetPrimaryNameWorkflow(BaseSingleStepContractWorkflow):
    """
    API ref: https://docs.ens.domains/contract-api-reference/reverseregistrar#set-name
    """
    WORKFLOW_TYPE = 'set-ens-primary-name'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict) -> None:
        self.domain = workflow_params['domain']

        user_description = f"Set ENS {self.domain} as primary name for wallet address '{wallet_address}'"

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, user_description, self.WORKFLOW_TYPE, workflow_params)

    def _general_workflow_validation(self):
        ens_update_common_pre_workflow_validation(self.web3_provider, self.domain, self.wallet_address)
        
    def _run(self) -> Result:
        reverse_registrar = get_ens_reverse_registrar_contract()

        tx_input = reverse_registrar.encodeABI(fn_name='setName', args=[self.domain])

        tx = {
            'to': reverse_registrar.address, 
            'data': tx_input,
        }
        
        return Result(
                status="success", 
                tx=tx,
                description=self.user_description
            )