from utils.abi.abi_loader import load_contract_abi
from ..base import Result, BaseSingleStepContractWorkflow, compute_abi_abspath, WorkflowValidationError
from typing import Any, Dict
from utils import hexify_token_amount
import context
LIDO_ADDRESS = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"

class LidoTextWorkflow(BaseSingleStepContractWorkflow):

    WORKFLOW_TYPE = 'deposit-eth-lido'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict) -> None:
        self.value = workflow_params['amount']

        user_description = f"Deposit {self.value} ETH to Lido"

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, user_description, workflow_type, workflow_params)
    
    def _general_workflow_validation(self):
        if int(self.value) <= 0:
            raise WorkflowValidationError("Amount must be positive")
    
    def _run(self) -> Result:
        web3_provider = self.web3_provider
        contract = web3_provider.eth.contract(address=LIDO_ADDRESS, abi=load_contract_abi(__file__, "abis/steth.abi.json"))
        tx = {
            'to': contract.address, 
            'data': contract.encodeABI(fn_name='submit', args=['0x0000000000000000000000000000000000000000']),
            'value': hexify_token_amount(self.wallet_chain_id, "ETH", self.value)
        }
        
        return Result(
            status= "success", 
            tx= tx,
            description= self.user_description
        )