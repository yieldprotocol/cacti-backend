import functools
import json
import re
import traceback
import context
import chat
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict, Callable
from utils import error_wrap, ConnectedWalletRequired, FetchError, ExecError
from chat.container import ContainerMixin, dataclass_to_container_params
from ui_workflows import (
    aave, ens, base
)
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus
)

class WorkflowClientPayload(TypedDict):
    id: str
    type: str
    step: base.WorkflowStepClientPayload

class MessagePayload(TypedDict):
    workflow: WorkflowClientPayload

@dataclass
class MultiStepPayloadContainer(ContainerMixin, base.MultiStepResult):

    @classmethod
    def from_multistep_result(cls, result: base.MultiStepResult):
        return cls(**asdict(result))

    def container_name(self) -> str:
        return 'display-multistep-payload-container'

    def container_params(self) -> Dict:
        return dataclass_to_container_params(self)
    

def process_multistep_workflow(payload: MessagePayload, send_message: Callable):
    print('Processing multistep workflow, ', payload)
    worklow = payload['workflow']
    workflow_id =  worklow['id']
    workflow_type = worklow['type']
    step = worklow['step']

    workflow_db_obj = MultiStepWorkflow.query.filter(MultiStepWorkflow.id == workflow_id).first()
    workflow_params = workflow_db_obj.params
    user_chat_message_id = workflow_db_obj.chat_message_id

    if workflow_type == ens.ENSRegistrationContractWorkflow.WORKFLOW_TYPE:
        result = register_ens_domain(workflow_params['domain'], user_chat_message_id, workflow_db_obj, step)
    elif workflow_type == aave.AaveSupplyContractWorkflow.WORKFLOW_TYPE:
        result = exec_aave_operation(workflow_params['token'], workflow_params['amount'], "supply", user_chat_message_id, workflow_db_obj, step)
    elif workflow_type == aave.AaveBorrowUIWorkflow.WORKFLOW_TYPE:
        result = exec_aave_operation(workflow_params['token'], workflow_params['amount'], "borrow", user_chat_message_id, workflow_db_obj, step)
    else:
        raise Exception(f'Workflow type {workflow_type} not supported.')
    
    if result.status != 'terminated':
        send_message(chat.Response(
                response=str(result),
                still_thinking=False,
                actor='bot',
                operation='create',
        ), last_chat_message_id=None)


@error_wrap
def register_ens_domain(domain: str, user_chat_message_id: str = None,  workflow: Optional[MultiStepWorkflow] = None, wf_step_client_payload: Optional[base.WorkflowStepClientPayload] = None) -> MultiStepPayloadContainer:
    wallet_chain_id = 1 # TODO: get from context
    wallet_address = context.get_wallet_address()
    user_chat_message_id = context.get_user_chat_message_id() or user_chat_message_id

    if not wallet_address:
        raise ConnectedWalletRequired

    wf = ens.ENSRegistrationContractWorkflow(wallet_chain_id, wallet_address, user_chat_message_id, {'domain': domain}, workflow, wf_step_client_payload)
    result = wf.run()

    return MultiStepPayloadContainer.from_multistep_result(result)

@error_wrap
def exec_aave_operation(token: str, amount: str, operation: Literal["supply", "borrow", "repay", "withdraw"], user_chat_message_id: str = None,  workflow: Optional[MultiStepWorkflow] = None, wf_step_client_payload: Optional[base.WorkflowStepClientPayload] = None) -> MultiStepPayloadContainer:
    wallet_chain_id = 1
    wallet_address = context.get_wallet_address()
    user_chat_message_id = context.get_user_chat_message_id() or user_chat_message_id
    workflow_params = {'token': token, 'amount': amount}

    if not wallet_address:
        raise ConnectedWalletRequired

    if operation == 'supply':
        wf = aave.AaveSupplyContractWorkflow(wallet_chain_id, wallet_address, user_chat_message_id, workflow_params, workflow, wf_step_client_payload)
    elif operation == 'borrow':
        wf = aave.AaveBorrowUIWorkflow(wallet_chain_id, wallet_address, user_chat_message_id, workflow_params, workflow, wf_step_client_payload)
    else:
        raise Exception(f'Operation {operation} not supported.')
    
    result = wf.run()

    return MultiStepPayloadContainer.from_multistep_result(result)