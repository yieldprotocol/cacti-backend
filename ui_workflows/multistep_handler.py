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

REGISTER_ENS_DOMAIN_WF_TYPE = 'register-ens-domain'

class WorkflowClientPayload(TypedDict):
    id: str
    type: str
    step: base.WorkflowStepClientPayload

class MessagePayload(TypedDict):
    workflow: WorkflowClientPayload

@dataclass
class MultiStepPayloadContainer(ContainerMixin):
    status: Literal['success', 'error']
    workflow_id: str
    workflow_type: str
    step_id: str
    step_type: str
    step_number: int
    total_steps: int
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
        result = register_ens_domain(workflow_params['domain'], user_chat_message_id, workflow_db_obj, step)

        if result.status != 'terminated':
            send_message(chat.Response(
                    response=str(result),
                    still_thinking=False,
                    actor='bot',
                    operation='create',
            ), last_chat_message_id=None)


@error_wrap
def register_ens_domain(domain: str, user_chat_message_id: str = None,  workflow: Optional[MultiStepWorkflow] = None, wf_step_client_payload: Optional[base.WorkflowStepClientPayload] = None) -> MultiStepPayloadContainer:
    wallet_chain_id = 1 # TODO: get constant from utils
    wallet_address = context.get_wallet_address()
    user_chat_message_id = context.get_user_chat_message_id() or user_chat_message_id

    if not wallet_address:
        raise ConnectedWalletRequired

    wf = ens.ENSRegistrationWorkflow(wallet_chain_id, wallet_address, user_chat_message_id, REGISTER_ENS_DOMAIN_WF_TYPE, {'domain': domain}, workflow, wf_step_client_payload)
    result = wf.run()

    return MultiStepPayloadContainer(
        status=result.status,
        workflow_id=result.workflow_id,
        workflow_type=result.workflow_type,
        step_id=result.step_id,
        step_type=result.step_type,
        step_number=result.step_number,
        total_steps=result.total_steps,
        user_action_type=result.user_action_type,
        tx=result.tx,
        error_msg=result.error_msg,
        description=result.description
    )





@dataclass
class TxPayloadForSending(ContainerMixin):
    user_request_status: Literal['success', 'error']
    parsed_user_request: str = ''
    tx: Optional[dict] = None  # from, to, value, data, gas
    is_approval_tx: bool = False
    error_msg: Optional[str] = None
    description: str = ''

    def container_name(self) -> str:
        return 'display-tx-payload-for-sending-container'

    def container_params(self) -> Dict:
        return dataclass_to_container_params(self)
    




@error_wrap
def ens_domain_setText(domain: str, 
                       user_chat_message_id: str = None,  
                       workflow: Optional[MultiStepWorkflow] = None,
                       wf_step_client_payload: Optional[base.WorkflowStepClientPayload] = None
                       ) ->TxPayloadForSending:
    wallet_chain_id = 1 # TODO: get constant from utils
    wallet_address = context.get_wallet_address()
    user_chat_message_id = context.get_user_chat_message_id() or user_chat_message_id

    if not wallet_address:
        raise ConnectedWalletRequired

    wf = ens.ENSSetText(wallet_chain_id, wallet_address, user_chat_message_id, params)
    result = wf.run()

    return TxPayloadForSending(
        status=result.status,
        parsed_user_request=result.parsed_user_request,
        tx=result.tx,
        error_msg=result.error_msg,
        description=result.description
    )


