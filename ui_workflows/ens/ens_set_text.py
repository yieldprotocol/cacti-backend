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
from ..base import tenderly_simulate_tx, Result, BaseContractSingleStepWorkflow, tenderly_simulate_tx, WorkflowValidationError
from .ens_utils import ENS_PUBLIC_RESOLVER_ADDRESS, ENS_REGISTRY_ADDRESS, get_node_namehash, is_domain_registered

class ENSSetTextWorkflow(BaseContractSingleStepWorkflow):
    """
    API ref: https://docs.ens.domains/contract-api-reference/publicresolver#set-text-data
    """
    def __init__(self, wallet_chain_id: int, wallet_address: str, workflow_type: str, workflow_params: Dict) -> None:
        self.domain = workflow_params['domain']
        self.key = workflow_params['key']
        self.value = workflow_params['value']
    
        user_description = f"Set field {self.key} to {self.value} for ENS domain {self.domain}"

        contract_address = ENS_PUBLIC_RESOLVER_ADDRESS
        abi_path = './ui_workflows/ens/abis/ens_resolver.abi'
        super().__init__(wallet_chain_id, wallet_address, contract_address, abi_path, user_description, workflow_type, workflow_params)
        
    def _pre_workflow_validation(self):
       # Check if domain is registered
       if (not is_domain_registered(self.domain)):
            raise WorkflowValidationError(f"ENS name {self.domain} is not registered")

    def _run(self) -> Result:
        # Create a contract object
        contract = w3.eth.contract(address=w3.toChecksumAddress(self.contract_address), abi=self.contract_abi_dict)
        
        # Construct the transaction input data
        node = get_node_namehash(self.domain)
        tx_input = contract.encodeABI(fn_name='setText', args=[node, self.key, self.value])

        tx = {
         'from': self.wallet_address, 
         'to': self.contract_address, 
         'data': tx_input
         }

        return Result(
                status="success", 
                tx=tx,
                description=self.user_description
            )