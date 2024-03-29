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

