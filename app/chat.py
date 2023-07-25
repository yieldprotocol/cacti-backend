from typing import Dict, Optional
from datetime import datetime
import uuid

from fastapi import Request
from sqlalchemy import insert

from database import utils as db_utils
from database.models import (
    db_session, ChatSession, ChatMessage, PrivacyType,
    SharedSession, SharedMessage,
)
import auth


@db_utils.close_db_session()
@auth.authenticate_user_id()
def get_settings(request: Request, chat_session_id: str, user_id: Optional[str] = None) -> Dict:
    # Get visibility settings for a chat session
    ret = {}
    chat_session = ChatSession.query.get(chat_session_id)
    if not chat_session:
        return ret

    if not user_id and chat_session.privacy_type != PrivacyType.public:
        return ret

    is_deleted = chat_session.deleted is not None
    if is_deleted and str(chat_session.user_id) != user_id:
        return ret

    if is_deleted:
        ret['visibility'] = 'deleted'
    elif chat_session.privacy_type == PrivacyType.public:
        ret['visibility'] = 'public'
    elif chat_session.privacy_type == PrivacyType.private:
        ret['visibility'] = 'private'

    if chat_session.name:
        ret['name'] = chat_session.name

    # data about whether you have permissions to edit
    can_edit = user_id is not None and str(chat_session.user_id) == user_id
    ret['canEdit'] = can_edit

    return ret


@db_utils.close_db_session()
@auth.authenticate_user_id()
def update_settings(request: Request, chat_session_id: str, data: auth.AcceptJSON, user_id: Optional[str] = None) -> bool:
    # for now, just support toggling privacy, if you own it
    if not user_id:
        return False

    chat_session = ChatSession.query.get(chat_session_id)
    if not chat_session:
        return False

    if chat_session.deleted is not None:
        return False

    if str(chat_session.user_id) != user_id:
        return False

    visibility = data.get("visibility")
    if visibility == "public":
        chat_session.privacy_type = PrivacyType.public
    elif visibility == "private":
        chat_session.privacy_type = PrivacyType.private

    name = data.get("name")
    if name:
        chat_session.name = name

    db_session.add(chat_session)
    db_session.commit()
    return True


@db_utils.close_db_session()
@auth.authenticate_user_id()
def delete_chat(request: Request, chat_session_id: str, user_id: Optional[str] = None) -> bool:
    if not user_id:
        return False

    chat_session = ChatSession.query.get(chat_session_id)
    if not chat_session:
        return False

    if chat_session.deleted is not None:
        return False

    if str(chat_session.user_id) != user_id:
        return False

    chat_session.deleted = datetime.utcnow()

    db_session.add(chat_session)
    db_session.commit()
    return True


@db_utils.close_db_session()
@auth.authenticate_user_id()
def list_chats(request: Request, user_id: Optional[str] = None) -> Dict:
    # Currently these return the chats you own, but in future, could expand
    # to chats that are shared with you or that you recently visited

    if not user_id:
        return {}

    # Return dictionary of list of sessions
    sessions = []
    for chat_session in ChatSession.query.filter(
            ChatSession.user_id == user_id, ChatSession.deleted == None
    ).order_by(ChatSession.created.desc()).all():
        sessions.append(dict(
            id=chat_session.id,
            created=chat_session.created,
            name=chat_session.name,
        ))
    return dict(
        sessions=sessions,
    )


@db_utils.close_db_session()
@auth.authenticate_user_id()
def import_chat_from_share(request: Request, data: auth.AcceptJSON, user_id: Optional[str] = None) -> Optional[str]:
    # Import a shared session into a new regular chat session
    shared_session_id = data.get("sharedSessionId")
    if not shared_session_id:
        return None

    if not user_id:
        return None

    shared_session = SharedSession.query.get(shared_session_id)
    if not shared_session:
        return None

    if shared_session.deleted is not None:
        return None

    # create new chat session
    chat_session_id = uuid.uuid4()
    chat_session = ChatSession(
        id=chat_session_id,
        user_id=user_id,
        name=shared_session.name,
        source_shared_session_id=shared_session_id,
    )
    db_session.add(chat_session)
    db_session.flush()

    # copy over messages
    chat_messages = []
    for source_message in SharedMessage.query.filter(
            SharedMessage.shared_session_id == shared_session_id
    ).order_by(SharedMessage.sequence_number, SharedMessage.created).all():
        chat_message = dict(
            actor=source_message.actor,
            type=source_message.type,
            payload=source_message.payload,
            sequence_number=source_message.sequence_number,
            chat_session_id=chat_session_id,
            system_config_id=source_message.system_config_id,
            source_shared_message_id=source_message.id,
        )
        chat_messages.append(chat_message)
    db_session.execute(insert(ChatMessage), chat_messages)
    db_session.commit()

    return str(chat_session_id)
