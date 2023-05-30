from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from dataclasses import dataclass
import json

import context

from web3 import Web3

class BaseContractWorkflow(ABC):
    """Grandparent base class for contract workflows. Do not directly use this class, use either BaseSingleStepContractWorkflow or BaseMultiStepContractWorkflow class"""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict) -> None:
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.chat_message_id = chat_message_id
        self.workflow_type = workflow_type
        self.workflow_params = workflow_params
        self.web3_provider = context.get_web3_provider()

    def run(self) -> Any:
        """Main function to call to run the workflow."""
        ret = self._run()
        return ret

    @abstractmethod
    def _run(self) -> Any:
        """Implement the contract interaction logic here."""


    @abstractmethod
    def _general_workflow_validation(self):
        """Override this method to perform any common validation checks for all steps in the workflow before running them"""

