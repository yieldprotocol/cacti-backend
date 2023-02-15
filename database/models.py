from typing import List, Optional
import uuid

import sqlalchemy  # type: ignore
from sqlalchemy import (  # type: ignore
    create_engine, func,
    Column, Index, Integer, String, JSON, Boolean,
    ForeignKey,
)
from sqlalchemy.orm import (  # type: ignore
    scoped_session, sessionmaker, relationship,
    backref)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base  # type: ignore
from sqlalchemy_utils import ChoiceType, Timestamp  # type: ignore

import utils


engine = create_engine(utils.CHATDB_URL)  # type: ignore
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base = declarative_base()
# We will need this for querying
Base.query = db_session.query_property()


class ChatSession(Base, Timestamp):  # type: ignore
    __tablename__ = 'chat_session'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class ChatMessage(Base, Timestamp):  # type: ignore
    __tablename__ = 'chat_message'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor = Column(String, nullable=False)
    type = Column(String, nullable=False)
    payload = Column(String, nullable=False)

    chat_session_id = Column(UUID(as_uuid=True), ForeignKey('chat_session.id'), nullable=False)
    chat_session = relationship(
        ChatSession,
        backref=backref('chat_messages',
                        uselist=True,
                        cascade='delete,all'))
