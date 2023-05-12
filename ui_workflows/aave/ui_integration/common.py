
from ...base import BaseUIWorkflow, MultiStepResult, BaseMultiStepUIWorkflow, WorkflowStepClientPayload, StepProcessingResult, RunnableStep, tenderly_simulate_tx, setup_mock_db_objects, process_result_and_simulate_tx, fetch_multistep_workflow_from_db


class AaveMixin:
    def _goto_page_and_open_walletconnect(self, page):
        """Go to page and open WalletConnect modal"""
        page.goto("https://app.aave.com/")
        page.get_by_role("button", name="wallet", exact=True).click()
        page.get_by_role("button", name="WalletConnect browser wallet icon").click()
