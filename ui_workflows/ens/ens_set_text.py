import re
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from web3 import Web3

from ..base import Result, BaseSingleStepContractWorkflow, WorkflowValidationError
from .ens_utils import ENS_PUBLIC_RESOLVER_ADDRESS, ENS_REGISTRY_ADDRESS, get_node_namehash, is_domain_registered, is_domain_owner


class ENSSetTextWorkflow(BaseSingleStepContractWorkflow):
    """
    API ref: https://docs.ens.domains/contract-api-reference/publicresolver#set-text-data
    """
    WORKFLOW_TYPE = 'set-ens-text'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict) -> None:
        self.domain = workflow_params['domain']
        self.key = workflow_params['key']
        self.value = workflow_params['value']
        self.contract_address =  Web3.to_checksum_address(ENS_PUBLIC_RESOLVER_ADDRESS)
        self.contract_abi_dict = self._load_contract_abi_dict(__file__, './abis/ens_resolver.abi.json')

        user_description = f"Set field {self.key} to {self.value} for ENS domain {self.domain}"

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, user_description, self.WORKFLOW_TYPE, workflow_params)
        
    def _pre_workflow_validation(self):
       # Check if domain is registered
        if (not is_domain_registered(self.web3_provider, self.domain)):
            raise WorkflowValidationError(f"ENS name {self.domain} is not registered")
    
        if(not is_domain_owner(self.web3_provider, self.domain, self.wallet_address)):
            raise WorkflowValidationError(f"ENS name {self.domain} is not owned by the user")

    def _run(self) -> Result:
        # Create a contract object
        contract = self.web3_provider.eth.contract(address=self.contract_address, abi=self.contract_abi_dict)
        
        # Construct the transaction input data
        node = get_node_namehash(self.domain)
        tx_input = contract.encodeABI(fn_name='setText', args=[node, self.key, self.value])

        tx = {
            'from': self.wallet_address, 
            'to': self.contract_address, 
            'data': tx_input,
            'value': '0x0',
        }
        
        return Result(
                status="success", 
                tx=tx,
                description=self.user_description
            )