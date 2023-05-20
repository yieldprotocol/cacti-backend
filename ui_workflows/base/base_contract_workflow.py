from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from dataclasses import dataclass

import json
from utils import w3
from .common import _validate_non_zero_eth_balance, compute_abi_abspath

class BaseContractWorkflow(ABC):
    """Grandparent base class for contract workflows. Do not directly use this class, use either BaseSingleStepContractWorkflow or BaseMultiStepContractWorkflow class"""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict, fork_id=None) -> None:
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = w3.to_checksum_address(wallet_address)
        self.chat_message_id = chat_message_id
        self.workflow_type = workflow_type
        self.workflow_params = workflow_params
        self.fork_id = fork_id

    def run(self) -> Any:
        """Main function to call to run the workflow."""
        _validate_non_zero_eth_balance(self.wallet_address)
        self._pre_workflow_validation()

        ret = self._run()
        return ret

    @abstractmethod
    def _run(self) -> Any:
        """Implement the contract interaction logic here."""

    @abstractmethod
    def _pre_workflow_validation(self):
        """Perform any validation before running the workflow."""
    
    def _load_contract_abi_dict(self, wf_file_path: str, abi_relative_path: str) -> Dict:
        abi_abs_path = compute_abi_abspath(wf_file_path, abi_relative_path)
        with open(abi_abs_path, 'r') as f:
            return json.load(f)

    

