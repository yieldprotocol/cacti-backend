from typing import Dict

from fastapi import Request

from database import utils as db_utils
from database.models import (
    db_session, ChatSession, PrivacyType,
)
import auth


@db_utils.close_db_session()
def handle_share(request: Request, data: auth.AcceptJSON) -> bool:
    user_id = auth.fetch_authenticated_user_id(request)
    if not user_id:
        return False

    # for now, just support toggling privacy, if you own it
    chat_session_id = data.get("chat_session_id")
    if not chat_session_id:
        return False

    chat_session = ChatSession.query.get(chat_session_id)
    if not chat_session:
        return False

    if str(chat_session.user_id) != user_id:
        return False

    operation = data.get("operation")
    if operation == "public":
        chat_session.privacy_type = PrivacyType.public
    elif operation == "private":
        chat_session.privacy_type = PrivacyType.private
    else:
        return False

    db_session.add(chat_session)
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
    for chat_session in ChatSession.query.filter(ChatSession.user_id == user_id).all():
        sessions.append(dict(
            id=chat_session.id,
            created=chat_session.created,
        ))
    return dict(
        sessions=sessions,
    )
