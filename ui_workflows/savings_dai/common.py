import os
import re
import json
from typing import Optional, Union, Literal

import context
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from web3 import Web3

from utils import load_contract_abi
from ..base import StepProcessingResult, revoke_erc20_approval, set_erc20_allowance, TEST_WALLET_ADDRESS, USDC_ADDRESS, WorkflowValidationError, ContractStepProcessingResult, BaseContractWorkflow

SAVINGS_DAI_ADDRESS = Web3.to_checksum_address("0x83F20F44975D03b1b09e64809B757c47f942BEeA")

def get_savings_dai_address_contract():
    web3_provider = context.get_web3_provider()
    return web3_provider.eth.contract(address=SAVINGS_DAI_ADDRESS, abi=load_contract_abi(__file__, "./abis/savings_dai.abi.json"))

def savings_dai_check_for_error_and_compute_result(contract_workflow: BaseContractWorkflow, tx):
    error_message = contract_workflow._simulate_tx_for_error_check(tx)
    if error_message:
        return ContractStepProcessingResult(status="error", error_msg=error_message)
    else:
        return ContractStepProcessingResult(status="success", tx=tx)  
