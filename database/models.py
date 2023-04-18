from typing import List, Optional
import enum
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
from sqlalchemy.dialects.postgresql import UUID, JSONB
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


class FeedbackStatus(enum.IntEnum):
    none = 1
    good = 2
    bad = 3
    neutral = 4

class WorkflowStepStatus(enum.IntEnum):
    pending = 1
    success = 2
    error = 3
    user_interrupt = 4

class SystemConfig(Base, Timestamp):  # type: ignore
    __tablename__ = 'system_config'
    id = Column(Integer, primary_key=True)
    json = Column(JSONB, nullable=False, index=True)


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

    system_config_id = Column(Integer, ForeignKey('system_config.id'), nullable=False)


Index('chat_message_by_session', ChatMessage.chat_session_id, ChatMessage.created)


class ChatMessageFeedback(Base, Timestamp):  # type: ignore
    __tablename__ = 'chat_message_feedback'
    chat_message_id = Column(UUID(as_uuid=True), ForeignKey('chat_message.id'), nullable=False, primary_key=True)
    chat_message = relationship(
        ChatMessage,
        backref=backref('chat_message_feedback',
                        uselist=False,
                        cascade='delete'))

    feedback_status = Column(ChoiceType(FeedbackStatus, impl=Integer()), default=FeedbackStatus.none, nullable=False)


class Workflow(Base, Timestamp):
    __tablename__ = 'workflow'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_session.id'), nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey('chat_message.id'), nullable=False)
    operation = Column(String, nullable=False)
    params = Column(JSONB, nullable=True)


class WorkflowStep(Base, Timestamp):
    __tablename__ = 'workflow_step'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflow.id'), nullable=False)
    step = Column(String, nullable=False)
    status = Column(ChoiceType(WorkflowStepStatus, impl=Integer()), default=WorkflowStepStatus.pending, nullable=False)
    status_message = Column(String, nullable=True)
    step_state = Column(JSONB, nullable=True)