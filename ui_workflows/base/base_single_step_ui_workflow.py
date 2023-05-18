import re
import traceback
from abc import abstractmethod
from logging import basicConfig, INFO

from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypedDict

from .base_ui_workflow import BaseUIWorkflow
from .common import Result, WorkflowValidationError, StepProcessingResult

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class BaseSingleStepUIWorkflow(BaseUIWorkflow):

    def __init__(self, wallet_chain_id: int, wallet_address: str, chat_message_id: str, workflow_type: str, workflow_params: Dict, user_description: str) -> None:
        self.chat_message_id = chat_message_id
        self.workflow_type = workflow_type
        self.workflow_params = workflow_params
        self.user_description = user_description
        self.log_params = f"wf_type: {self.workflow_type}, chat_message_id: {self.chat_message_id}, wf_params: {self.workflow_params}"
        super().__init__(wallet_chain_id, wallet_address)

    def run(self) -> Any:
        print(f"Single-step UI workflow started, {self.log_params}")
        try:
            # Arbitrary wait to allow for enough time for WalletConnect relay to send our client the tx data
            return super().run()
        except WorkflowValidationError as e:
            print(f"SINGLE STEP UI WORKFLOW VALIDATION ERROR, {self.log_params}")
            traceback.print_exc()
            return Result(
                status='error',
                error_msg=e.args[0],
                description=self.user_description
            )
        except Exception:
            print(f"SINGLE STEP UI WORKFLOW EXCEPTION, {self.log_params}")
            traceback.print_exc()
            return Result(
                status='error',
                error_msg="Unexpected error. Check with support.",
                description=self.user_description
            )
        finally:
            self.stop_listener()
            print(f"Single-step UI workflow ended, {self.log_params}")

    
    def _run_page(self, page, context) -> Result:
        processing_result = self._run_step(page, context)

        computed_user_description = processing_result.override_user_description or self.user_description

        # Arbitrary wait to allow for enough time for WalletConnect relay to send our client the tx data
        page.wait_for_timeout(5000)
        tx = self.stop_listener()
        return Result(
            status=processing_result.status,
            tx=tx,
            error_msg=processing_result.error_msg,
            description=computed_user_description,
        )

    @abstractmethod
    def _run_step(self, page, context) -> StepProcessingResult:
        """Run the step and return the result."""

        
        
