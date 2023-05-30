import re
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from dataclasses import dataclass, asdict

from web3 import Web3

from ...base import Result, BaseSingleStepContractWorkflow, WorkflowValidationError
from ..common import get_ens_reverse_registrar_contract, ens_update_common_pre_workflow_validation
from .ens_set_text import ENSSetTextWorkflow


class ENSSetAvatarNFTWorkflow(BaseSingleStepContractWorkflow):
    """
    Workflow to set an avatar represented by an NFT for an ENS domain
    ref: https://medium.com/@brantly.eth/step-by-step-guide-to-setting-an-nft-as-your-ens-profile-avatar-3562d39567fc
    """
    WORKFLOW_TYPE = 'set-ens-avatar-nft'

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_params: Dict) -> None:
        self.domain = workflow_params['domain']
        self.nftContractAddress = workflow_params['nftContractAddress']
        self.nftId = workflow_params['nftId']

        user_description = f"Set avatar for ENS '{self.domain}'"

        super().__init__(wallet_chain_id, wallet_address, chat_message_id, user_description, self.WORKFLOW_TYPE, workflow_params)

    def _general_workflow_validation(self):
        if not self.domain:
            raise WorkflowValidationError("Unable to interpret an ENS domain in current chat for setting avatar, please specify an ENS domain")

        if not self.nftContractAddress:
            raise WorkflowValidationError("Unable to interpret an NFT collection in current chat for setting avatar, ask for a collection first and try again")

        if not self.nftId:
            raise WorkflowValidationError("Unable to interpret an NFT ID in current chat for setting avatar, please specify an NFT ID")
        
        ens_update_common_pre_workflow_validation(self.web3_provider, self.domain, self.wallet_address)
        
    def _run(self) -> Result:
        params = {
            "domain": self.domain,
            "key": "avatar",
            "value": f"eip155:1/erc721:{self.nftContractAddress}/{self.nftId}"
        }

        result = ENSSetTextWorkflow(self.wallet_chain_id, self.wallet_address, self.chat_message_id, params).run()

        # Reset the description to be more specific to this workflow
        result.description = self.user_description

        return result