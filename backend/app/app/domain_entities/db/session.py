from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    _session = session_factory()
    yield _session
    _session.close()
