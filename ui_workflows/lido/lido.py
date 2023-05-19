from ..base import BaseSingleStepContractWorkflow, compute_abi_abspath
from typing import Any, Dict
LIDO_ADDRESS = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"

class LidoTextWorkflow(BaseSingleStepContractWorkflow):
    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict) -> None:
        self.value = workflow_params['value']

        user_description = f"Deposit {self.value} ETH to Lido"

        contract_address = LIDO_ADDRESS

        abi_path = compute_abi_abspath(__file__, './abis/lido.abi')
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, contract_address, abi_path, user_description, workflow_type, workflow_params)
        