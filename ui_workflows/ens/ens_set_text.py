import re
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from web3 import Web3

from ..base import Result, BaseSingleStepContractWorkflow, WorkflowValidationError
from .common import get_node_namehash, get_ens_resolver_contract, ens_update_common_pre_workflow_validation


class ENSSetTextWorkflow(BaseSingleStepContractWorkflow):
    """
    API ref: https://docs.ens.domains/contract-api-reference/publicresolver#set-text-data
    """
    WORKFLOW_TYPE = 'set-ens-text'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict) -> None:
        self.domain = workflow_params['domain']
        self.key = workflow_params['key']
        self.value = workflow_params['value']

        user_description = f"Set field {self.key} to {self.value} for ENS domain {self.domain}"

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, user_description, self.WORKFLOW_TYPE, workflow_params)

    def _general_workflow_validation(self):
        ens_update_common_pre_workflow_validation(self.web3_provider, self.domain, self.wallet_address)

    def _run(self) -> Result:
        resolver_contract = get_ens_resolver_contract()

        # Construct the transaction input data
        node = get_node_namehash(self.domain)
        tx_input = resolver_contract.encodeABI(fn_name='setText', args=[node, self.key, self.value])

        tx = {
            'to': resolver_contract.address, 
            'data': tx_input,
        }
        
        return Result(
                status="success", 
                tx=tx,
                description=self.user_description
            )