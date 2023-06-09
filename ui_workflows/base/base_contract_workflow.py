from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict
from dataclasses import dataclass
import requests

from web3 import Web3, exceptions

import context
import env
from utils import TENDERLY_API_KEY

class BaseContractWorkflow(ABC):
    """Grandparent base class for contract workflows. Do not directly use this class, use either BaseSingleStepContractWorkflow or BaseMultiStepContractWorkflow class"""

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict) -> None:
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.chat_message_id = chat_message_id
        self.workflow_type = workflow_type
        self.workflow_params = workflow_params
        self.web3_provider = context.get_web3_provider()

    @abstractmethod
    def _run(self) -> Any:
        """Implement the contract interaction logic here."""


    @abstractmethod
    def _general_workflow_validation(self):
        """Override this method to perform any common validation checks for all steps in the workflow before running them"""

    def run(self) -> Any:
        """Main function to call to run the workflow."""
        ret = self._run()
        return ret
    
    def _simulate_tx_for_error_check(self, tx: Dict) -> Optional[str]:
        if env.is_prod():
            tenderly_simulate_api_url = f"https://api.tenderly.co/api/v1/account/Yield/project/chatweb3/simulate"
        else:
            tenderly_simulate_api_url = f"https://api.tenderly.co/api/v1/account/Yield/project/chatweb3/fork/{context.get_web3_fork_id()}/simulate"
        
        payload = {
            "save": False, 
            "save_if_fails": False, 
            "simulation_type": "full",
            "network_id": self.wallet_chain_id,
            "from": tx['from'],
            "to": tx['to'],
            "input": tx['data'],
            "value": tx.get('value', 0),
        }

        res = requests.post(tenderly_simulate_api_url, json=payload, headers={'X-Access-Key': TENDERLY_API_KEY})

        if res.status_code == 200:
            simulation_data = res.json()
            transaction = simulation_data['transaction']
            error_message = transaction.get('error_message')
            return error_message
        else:
            return None



