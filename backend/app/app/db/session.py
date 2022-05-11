from typing import Generator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def get_engine():
    return create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)


session_factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator:
    _session = session_factory()
    yield _session
    _session.close()


def save(q: str = Depends(get_engine())):
    if not q:
        return 1
    return q
