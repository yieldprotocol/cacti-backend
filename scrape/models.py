# Generate schema: python3 -c "from scrape.models import engine, Base; Base.metadata.create_all(bind=engine)"

from datetime import datetime
import enum

import sqlalchemy  # type: ignore
from sqlalchemy import (  # type: ignore
    create_engine, func,
    Column, Index, Integer, String, JSON, Boolean,
    ForeignKey, DateTime,
)
from sqlalchemy.orm import (  # type: ignore
    scoped_session, sessionmaker, relationship,
    backref)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TEXT
from sqlalchemy.ext.declarative import declarative_base  # type: ignore
from sqlalchemy_utils import ChoiceType, Timestamp  # type: ignore

import utils


engine = create_engine(utils.SCRAPEDB_URL)  # type: ignore
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()


class ScrapedUrl(Base, Timestamp):  # type: ignore
    __tablename__ = 'scraped_url'
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    data = Column(JSONB, nullable=False)

    Index('scraped_url_lookup', url, unique=True)

class Dapp(Base):
    __tablename__ = 'dapps'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(TEXT, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    url = Column(String(255), nullable=False)
    twitter_handle = Column(String(255), nullable=True)
    blog_links = Column(ARRAY(String(255)), nullable=True)
    discord = Column(String(255), nullable=True)
    facebook = Column(String(255), nullable=True)
    instagram = Column(String(255), nullable=True)
    telegram = Column(String(255), nullable=True)

    Index('dapp_name_url_index', 'name', 'url', unique=True)
