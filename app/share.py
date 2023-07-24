from typing import Dict, Optional
import uuid

from fastapi import Request

from database import utils as db_utils
from database.models import (
    db_session, ChatSession, ChatMessage, PrivacyType,
    SharedSession, SharedMessage,
)
import auth


@db_utils.close_db_session()
@auth.authenticate_user_id()
def create_share(request: Request, data: auth.AcceptJSON, user_id: Optional[str] = None) -> Optional[str]:
    # Share an existing session as a new shared session
    source_session_id = data.get('chatSessionId')
    if not source_session_id:
        return None

    if not user_id:
        return None

    source_session = ChatSession.query.get(source_session_id)
    if not source_session:
        return None

    if source_session.deleted is not None:
        return None

    # only allow sharing if you can view the session
    if str(source_session.user_id) != user_id and source_session.privacy_type != PrivacyType.public:
        return None

    # create new shared session
    shared_session_id = uuid.uuid4()
    shared_session = SharedSession(
        id=shared_session_id,
        user_id=user_id,
        name=source_session.name,
        source_chat_session_id=source_session.id,
    )
    db_session.add(shared_session)
    db_session.flush()

    # copy over messages
    for source_message in ChatMessage.query.filter(
            ChatMessage.chat_session_id == source_session_id
    ).order_by(ChatMessage.sequence_number, ChatMessage.created).all():
        shared_message = SharedMessage(
            actor=source_message.actor,
            type=source_message.type,
            payload=source_message.payload,
            sequence_number=source_message.sequence_number,
            shared_session_id=shared_session_id,
            system_config_id=source_message.system_config_id,
            source_chat_message_id=source_message.id,
        )
        db_session.add(shared_message)
        db_session.flush()
    db_session.commit()

    return str(shared_session_id)


@db_utils.close_db_session()
def view_share(request: Request, shared_session_id: str) -> Dict:
    # view a shared session by its id
    ret = {}
    shared_session = SharedSession.query.get(shared_session_id)
    if not shared_session:
        return ret

    if shared_session.deleted is not None:
        return ret

    if shared_session.name:
        ret['name'] = shared_session.name
    messages = []
    for shared_message in SharedMessage.query.filter(
            SharedMessage.shared_session_id == shared_session_id
    ).order_by(SharedMessage.sequence_number, SharedMessage.created).all():
        messages.append({
            'messageId': shared_message.id,
            'actor': shared_message.actor,
            'type': shared_message.type,
            'payload': shared_message.payload,
            'feedback': 'n/a',
        })
    ret['messages'] = messages

    return ret


@db_utils.close_db_session()
@auth.authenticate_user_id()
def update_share(request: Request, shared_session_id: str, data: auth.AcceptJSON, user_id: Optional[str] = None) -> bool:
    if not user_id:
        return False

    shared_session = SharedSession.query.get(shared_session_id)
    if not shared_session:
        return False

    if shared_session.deleted is not None:
        return False

    if str(shared_session.user_id) != user_id:
        return False

    name = data.get("name")
    if name:
        shared_session.name = name

    db_session.add(shared_session)
    db_session.commit()
    return True


@db_utils.close_db_session()
@auth.authenticate_user_id()
def list_shares(request: Request, user_id: Optional[str] = None) -> Dict:
    # Currently these return your shared links
    if not user_id:
        return {}

    # Return dictionary of list of shared sessions
    shares = []
    for shared_session in SharedSession.query.filter(
            SharedSession.user_id == user_id, SharedSession.deleted == None
    ).order_by(SharedSession.created.desc()).all():
        shares.append(dict(
            id=shared_session.id,
            created=shared_session.created,
            name=shared_session.name,
        ))
    return dict(
        shares=shares,
    )
