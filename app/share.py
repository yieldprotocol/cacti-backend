from typing import Dict, Optional
import uuid

from fastapi import Request

from database import utils as db_utils
from database.models import (
    db_session, ChatSession, ChatMessage, PrivacyType,
)
import auth


@db_utils.close_db_session()
def get_settings(request: Request, chat_session_id: str) -> Dict:
    # Get visibility settings for a chat session
    chat_session = ChatSession.query.get(chat_session_id)
    if not chat_session:
        return {}

    user_id = auth.fetch_authenticated_user_id(request)
    if not user_id and chat_session.privacy_type != PrivacyType.public:
        return {}

    ret = {}
    if chat_session.privacy_type == PrivacyType.public:
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
def update_settings(request: Request, chat_session_id: str, data: auth.AcceptJSON) -> bool:
    # for now, just support toggling privacy, if you own it
    user_id = auth.fetch_authenticated_user_id(request)
    if not user_id:
        return False

    chat_session = ChatSession.query.get(chat_session_id)
    if not chat_session:
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
def clone_session(request: Request, source_session_id: str, data: auth.AcceptJSON) -> Optional[str]:
    # Clone an existing session into a new session
    user_id = auth.fetch_authenticated_user_id(request)
    if not user_id:
        return None

    source_session = ChatSession.query.get(source_session_id)
    if not source_session:
        return None

    # only allow cloning if you can view the session
    if str(source_session.user_id) != user_id and source_session.privacy_type != PrivacyType.public:
        return None

    # create new session
    target_session_id = uuid.uuid4()
    target_session = ChatSession(id=target_session_id, user_id=user_id)
    db_session.add(target_session)
    db_session.flush()

    # copy over messages
    for source_message in ChatMessage.query.filter(
            ChatMessage.chat_session_id == source_session_id
    ).order_by(ChatMessage.sequence_number, ChatMessage.created).all():
        target_message = ChatMessage(
            actor=source_message.actor,
            type=source_message.type,
            payload=source_message.payload,
            sequence_number=source_message.sequence_number,
            chat_session_id=target_session_id,
            system_config_id=source_message.system_config_id,
        )
        db_session.add(target_message)
        db_session.flush()
    db_session.commit()

    return str(target_session_id)


@db_utils.close_db_session()
def get_visible_chats(request: Request) -> Dict:
    # Currently these return the chats you own, but in future, could expand
    # to chats that are shared with you or that you recently visited

    user_id = auth.fetch_authenticated_user_id(request)
    if not user_id:
        return {}

    # Return dictionary of list of sessions
    sessions = []
    for chat_session in ChatSession.query.filter(ChatSession.user_id == user_id).order_by(ChatSession.created.desc()).all():
        sessions.append(dict(
            id=chat_session.id,
            created=chat_session.created,
            name=chat_session.name,
        ))
    return dict(
        sessions=sessions,
    )
