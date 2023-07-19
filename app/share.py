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
def create_share(request: Request, source_session_id: str, data: auth.AcceptJSON) -> Optional[str]:
    # Share an existing session as a new shared session
    user_id = auth.fetch_authenticated_user_id(request)
    if not user_id:
        return None

    source_session = ChatSession.query.get(source_session_id)
    if not source_session:
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
def import_share(request: Request, shared_session_id: str, data: auth.AcceptJSON) -> Optional[str]:
    # Import a shared session into a new regular chat session
    user_id = auth.fetch_authenticated_user_id(request)
    if not user_id:
        return None

    shared_session = SharedSession.query.get(shared_session_id)
    if not shared_session:
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
    for source_message in SharedMessage.query.filter(
            SharedMessage.shared_session_id == shared_session_id
    ).order_by(SharedMessage.sequence_number, SharedMessage.created).all():
        chat_message = ChatMessage(
            actor=source_message.actor,
            type=source_message.type,
            payload=source_message.payload,
            sequence_number=source_message.sequence_number,
            chat_session_id=chat_session_id,
            system_config_id=source_message.system_config_id,
            source_shared_message_id=source_message.id,
        )
        db_session.add(chat_message)
        db_session.flush()
    db_session.commit()

    return str(chat_session_id)


@db_utils.close_db_session()
def view_share(request: Request, shared_session_id: str) -> Dict:
    # view a shared session by its id
    shared_session = SharedSession.query.get(shared_session_id)
    if not shared_session:
        return {}

    ret = {}
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
def update_share(request: Request, shared_session_id: str, data: auth.AcceptJSON) -> bool:
    user_id = auth.fetch_authenticated_user_id(request)
    if not user_id:
        return False

    shared_session = SharedSession.query.get(shared_session_id)
    if not shared_session:
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


@db_utils.close_db_session()
def get_visible_shares(request: Request) -> Dict:
    # Currently these return your shared links

    user_id = auth.fetch_authenticated_user_id(request)
    if not user_id:
        return {}

    # Return dictionary of list of shared sessions
    shares = []
    for shared_session in SharedSession.query.filter(SharedSession.user_id == user_id).order_by(SharedSession.created.desc()).all():
        shares.append(dict(
            id=shared_session.id,
            created=shared_session.created,
            name=shared_session.name,
        ))
    return dict(
        shares=shares,
    )
