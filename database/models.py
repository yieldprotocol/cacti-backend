from typing import List, Optional
import enum
import uuid

import sqlalchemy  # type: ignore
from sqlalchemy import (  # type: ignore
    create_engine, func,
    Column, Index, Integer, String, JSON, Boolean,
    ForeignKey, DateTime,
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

class WorkflowStepUserActionType(enum.IntEnum):
    none = 1
    tx = 2
    acknowledge = 3

class PrivacyType(enum.IntEnum):
    private = 1
    public = 2


class SystemConfig(Base, Timestamp):  # type: ignore
    __tablename__ = 'system_config'
    id = Column(Integer, primary_key=True)
    json = Column(JSONB, nullable=False, index=True)


class User(Base, Timestamp):  # type: ignore
    __tablename__ = 'user'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Wallet(Base, Timestamp):  # type: ignore
    __tablename__ = 'wallet'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_address = Column(String, nullable=False)

    Index('wallet_address_unique', wallet_address, unique=True)


class UserWallet(Base, Timestamp):  # type: ignore
    __tablename__ = 'user_wallet'
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=False, primary_key=True)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('wallet.id'), nullable=False, primary_key=True)

    Index('wallet_user_id', wallet_id, user_id)


class ChatSession(Base, Timestamp):  # type: ignore
    __tablename__ = 'chat_session'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    privacy_type = Column(ChoiceType(PrivacyType, impl=Integer()), server_default=str(int(PrivacyType.private)), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=True)
    name = Column(String, nullable=True)
    deleted = Column(DateTime, nullable=True)

    source_shared_session_id = Column(UUID(as_uuid=True), nullable=True)


Index('chat_session_by_user_deleted_created', ChatSession.user_id, ChatSession.deleted, ChatSession.created)


class ChatMessage(Base, Timestamp):  # type: ignore
    __tablename__ = 'chat_message'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor = Column(String, nullable=False)
    type = Column(String, nullable=False)
    payload = Column(String, nullable=False)
    sequence_number = Column(Integer, nullable=False, default=0)

    chat_session_id = Column(UUID(as_uuid=True), ForeignKey('chat_session.id'), nullable=False)
    chat_session = relationship(
        ChatSession,
        backref=backref('chat_messages',
                        uselist=True,
                        cascade='delete,all'))

    system_config_id = Column(Integer, ForeignKey('system_config.id'), nullable=False)

    source_shared_message_id = Column(UUID(as_uuid=True), nullable=True)


Index('chat_message_by_sequence_number', ChatMessage.chat_session_id, ChatMessage.sequence_number, ChatMessage.created)


class SharedSession(Base, Timestamp):  # type: ignore
    __tablename__ = 'shared_session'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=True)
    name = Column(String, nullable=True)
    deleted = Column(DateTime, nullable=True)

    source_chat_session_id = Column(UUID(as_uuid=True), ForeignKey('chat_session.id'), nullable=False)


Index('shared_session_by_user_deleted_created', SharedSession.user_id, SharedSession.deleted, SharedSession.created)


class SharedMessage(Base, Timestamp):  # type: ignore
    __tablename__ = 'shared_message'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor = Column(String, nullable=False)
    type = Column(String, nullable=False)
    payload = Column(String, nullable=False)
    sequence_number = Column(Integer, nullable=False, default=0)

    shared_session_id = Column(UUID(as_uuid=True), ForeignKey('shared_session.id'), nullable=False)
    shared_session = relationship(
        SharedSession,
        backref=backref('shared_messages',
                        uselist=True,
                        cascade='delete,all'))

    system_config_id = Column(Integer, ForeignKey('system_config.id'), nullable=False)

    source_chat_message_id = Column(UUID(as_uuid=True), ForeignKey('chat_message.id'), nullable=False)


Index('shared_message_by_sequence_number', SharedMessage.shared_session_id, SharedMessage.sequence_number, SharedMessage.created)


class ChatMessageFeedback(Base, Timestamp):  # type: ignore
    __tablename__ = 'chat_message_feedback'
    chat_message_id = Column(UUID(as_uuid=True), ForeignKey('chat_message.id'), nullable=False, primary_key=True)
    chat_message = relationship(
        ChatMessage,
        backref=backref('chat_message_feedback',
                        uselist=False,
                        cascade='delete,all'))

    feedback_status = Column(ChoiceType(FeedbackStatus, impl=Integer()), default=FeedbackStatus.none, nullable=False)


class MultiStepWorkflow(Base, Timestamp):
    __tablename__ = 'multistep_workflow'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_message_id = Column(UUID(as_uuid=True), nullable=True)
    wallet_address = Column(String, nullable=False)
    wallet_chain_id = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    params = Column(JSONB, nullable=True)


class WorkflowStep(Base, Timestamp):
    __tablename__ = 'workflow_step'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('multistep_workflow.id'), nullable=False)
    type = Column(String, nullable=False)
    step_number = Column(Integer, nullable=False)
    user_action_type = Column(ChoiceType(WorkflowStepUserActionType, impl=Integer()), default=WorkflowStepUserActionType.none, nullable=False)
    user_action_data = Column(String, nullable=True)
    status = Column(ChoiceType(WorkflowStepStatus, impl=Integer()), default=WorkflowStepStatus.pending, nullable=False)
    status_message = Column(String, nullable=True)
    step_state = Column(JSONB, nullable=True)
