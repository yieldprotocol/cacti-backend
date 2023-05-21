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

from utils import estimate_gas
from .common import WorkflowValidationError, Result
from .base_contract_workflow import BaseContractWorkflow

class BaseSingleStepContractWorkflow(BaseContractWorkflow):
    
    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, user_description: str, workflow_type: str, workflow_params: Dict) -> None:
        super().__init__(wallet_chain_id, wallet_address, chat_message_id, workflow_type, workflow_params)
        
        self.user_description = user_description        
        self.log_params = f"wf_type: {self.workflow_type}, chat_message_id: {self.chat_message_id}, wf_params: {self.workflow_params}"


    def run(self) -> Result:
        print(f"Single-step contract workflow started, {self.log_params}")
        try:
            result: Result = super().run()

            tx = result.tx
            tx['gas'] = estimate_gas(tx)

            return result
        except WorkflowValidationError as e:
            print(f"SINGLE STEP CONTRACT WORKFLOW VALIDATION ERROR, {self.log_params}")
            traceback.print_exc()
            return Result(
                status="error", 
                error_msg=e.args[0],
                description=self.user_description
            )
        except Exception as e:
            print(f"SINGLE STEP CONTRACT WORKFLOW EXCEPTION, {self.log_params}")
            traceback.print_exc()
            return Result(
                status="error", 
                error_msg="Unexpected error. Check with support.",
                description=self.user_description
            )
        finally:
            print(f"Single-step contract workflow ended, {self.log_params}")