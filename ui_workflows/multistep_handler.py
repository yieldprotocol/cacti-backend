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
    aave, ens
)
from database.models import (
    db_session, MultiStepWorkflow, WorkflowStep, WorkflowStepStatus
)

REGISTER_ENS_DOMAIN_WF_TYPE = 'register-ens-domain'

class WorkflowStepClientPayload(TypedDict):
    id: str
    type: str
    status: Literal['pending', 'success', 'error', 'user_interrupt']
    status_message: str

class WorkflowClientPayload(TypedDict):
    id: str
    type: str
    step: WorkflowStepClientPayload

class MessagePayload(TypedDict):
    workflow: WorkflowClientPayload

@dataclass
class MultiStepPayload(ContainerMixin):
    status: Literal['success', 'error']
    workflow_id: str
    workflow_type: str
    step_id: str
    step_type: str
    user_action_type: str
    tx: Optional[dict] = None  # from, to, value, data, gas
    error_msg: Optional[str] = None
    description: str = ''

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

    if workflow_type == REGISTER_ENS_DOMAIN_WF_TYPE:
        result = str(register_ens_domain(workflow_params['domain'], user_chat_message_id, workflow_id, step))
        send_message(chat.Response(
                response=result,
                still_thinking=False,
                actor='bot',
                operation='create',
        ), last_chat_message_id=None)


@error_wrap
def register_ens_domain(domain: str, user_chat_message_id: str = None,  workflow_id: Optional[str] = None, wf_step_client_payload: Optional[WorkflowStepClientPayload] = None) -> MultiStepPayload:
    wallet_chain_id = 1 # TODO: get constant from utils
    wallet_address = context.get_wallet_address()
    user_chat_message_id = context.get_user_chat_message_id() or user_chat_message_id

    if not wallet_address:
        raise ConnectedWalletRequired

    wf = ens.ENSRegistrationWorkflow(wallet_chain_id, wallet_address, user_chat_message_id, REGISTER_ENS_DOMAIN_WF_TYPE, workflow_id, {'domain': domain}, wf_step_client_payload)
    result = wf.run()

    return MultiStepPayload(
        status=result.status,
        workflow_id=result.workflow_id,
        workflow_type=result.workflow_type,
        step_id=result.step_id,
        step_type=result.step_type,
        user_action_type=result.user_action_type,
        tx=result.tx,
        error_msg=result.error_msg,
        description=result.description
    )