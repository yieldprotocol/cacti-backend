import re
from logging import basicConfig, INFO
import time
import json
import uuid
import os

from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

import env
from utils import TENDERLY_FORK_URL, w3
from ..base import tenderly_simulate_tx, Result, BaseSingleStepContractWorkflow, WorkflowValidationError, estimate_gas, compute_abi_abspath
from .ens_utils import ENS_PUBLIC_RESOLVER_ADDRESS, ENS_REGISTRY_ADDRESS, get_node_namehash, is_domain_registered

class ENSSetTextWorkflow(BaseSingleStepContractWorkflow):
    """
    API ref: https://docs.ens.domains/contract-api-reference/publicresolver#set-text-data
    """
    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict) -> None:
        self.domain = workflow_params['domain']
        self.key = workflow_params['key']
        self.value = workflow_params['value']
    
        user_description = f"Set field {self.key} to {self.value} for ENS domain {self.domain}"

        contract_address = ENS_PUBLIC_RESOLVER_ADDRESS

        abi_path = compute_abi_abspath(__file__, './abis/ens_resolver.abi')
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, contract_address, abi_path, user_description, workflow_type, workflow_params)
        
    def _pre_workflow_validation(self):
       # Check if domain is registered
       if (not is_domain_registered(self.domain)):
            raise WorkflowValidationError(f"ENS name {self.domain} is not registered")
    
        # TODO: check if user owns the domain

    def _run(self) -> Result:
        # Create a contract object
        contract = w3.eth.contract(address=self.contract_address, abi=self.contract_abi_dict)
        
        # Construct the transaction input data
        node = get_node_namehash(self.domain)
        tx_input = contract.encodeABI(fn_name='setText', args=[node, self.key, self.value])

        tx = {
            'from': self.wallet_address, 
            'to': self.contract_address, 
            'data': tx_input,
            'value': '0x0',
        }
        
        tx['gas'] = estimate_gas(tx)

        return Result(
                status="success", 
                tx=tx,
                description=self.user_description
            )