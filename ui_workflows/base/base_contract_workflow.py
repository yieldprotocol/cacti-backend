from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from dataclasses import dataclass

import json
from utils import w3
from .common import _validate_non_zero_eth_balance

class BaseContractWorkflow(ABC):
    """Grandparent base class for contract workflows. Do not directly use this class, use either BaseSingleStepContractWorkflow or BaseMultiStepContractWorkflow class"""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, contract_address: str, abi_path: str, workflow_type: str, workflow_params: Dict) -> None:
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = wallet_address
        self.chat_message_id = chat_message_id
        self.contract_address = w3.to_checksum_address(contract_address)
        self.abi_path = abi_path
        self.workflow_type = workflow_type
        self.workflow_params = workflow_params
        self.log_params = f"wf_type: {self.workflow_type}, chat_message_id: {self.chat_message_id}, wf_params: {self.workflow_params}"

    def run(self) -> Any:
        """Main function to call to run the workflow."""
        print(f"Contract workflow start, {self.log_params}")

        self._load_contract_abi()

        _validate_non_zero_eth_balance(self.wallet_address)
        self._pre_workflow_validation()

        ret = self._run()

        print(f"Contract workflow finished, {self.log_params}")
        return ret

    @abstractmethod
    def _run(self) -> Any:
        """Implement the contract interaction logic here."""

    @abstractmethod
    def _pre_workflow_validation(self):
        """Perform any validation before running the workflow."""

    def _load_contract_abi(self):
        """Load contract ABI from file."""
        with open(self.abi_path, 'r') as f:
            self.contract_abi_dict = json.load(f)

    

