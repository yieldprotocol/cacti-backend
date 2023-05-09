import threading
import time
import sys
import uuid
import os
import json
import traceback
import requests
from abc import ABC, abstractmethod
from typing import Dict

from .common import WorkflowValidationError, Result
from .base_contract_workflow import BaseContractWorkflow

class BaseContractSingleStepWorkflow(BaseContractWorkflow):
    def __init__(self, wallet_chain_id: int, wallet_address: str, contract_address: str, abi_path: str, user_description: str, workflow_type: str, workflow_params: Dict) -> None:
        self.user_description = user_description
        super().__init__(wallet_chain_id, wallet_address, contract_address, abi_path, workflow_type, workflow_params)

    def run(self) -> Result:
        try:
            return super().run()
        except WorkflowValidationError as e:
            print("CONTRACT SINGLE STEP WORKFLOW VALIDATION ERROR")
            traceback.print_exc()
            return Result(
                status="error", 
                error_msg=e.args[0],
                description=self.user_description
            )
        except Exception as e:
            print("CONTRACT SINGLE STEP WORKFLOW EXCEPTION")
            traceback.print_exc()
            return Result(
                status="error", 
                error_msg="Unexpected error. Check with support.",
                description=self.user_description
            )