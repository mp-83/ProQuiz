import os
from base64 import b64encode
from datetime import timedelta

import alembic
import alembic.command
import alembic.config
import pytest

from app import main
from app.entities import Game, Match, Question, User
from app.tests.fixtures import TEST_1
from sqlalchemy import event


from typing import Dict, Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.base import Base
from app.core.config import settings
from app.main import app
from app.core import security
from app.tests.utilities.user import authentication_token_from_email
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="module")
def client() -> Generator:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers() -> Dict[str, str]:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    a_token = {
        "access_token": security.create_access_token(
            1, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
    return {"Authorization": f"Bearer {a_token}"}


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> Dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )


class Cookie:
    def values(self):
        return []


@pytest.fixture(scope="session")
def testapp():
    yield


def pytest_addoption(parser):
    parser.addoption("--ini", action="store", metavar="INI_FILE")


@pytest.fixture(scope="session")
def ini_file(request):
    # potentially grab this path from a pytest option
    return os.path.abspath("pytest.ini")


@pytest.fixture(scope="session")
def alembic_ini_file(request):
    return os.path.abspath("alembic.ini")


@pytest.fixture(scope="session")
def db_engine() -> Generator:
    alembic_cfg = alembic.config.Config(alembic_ini_file)
    engine = create_engine("sqlite:///:memory:", pool_pre_ping=True)
    Base.metadata.drop_all(bind=engine)
    alembic.command.stamp(alembic_cfg, None, purge=True)

    # run migrations to initialize the database
    # depending on how we want to initialize the database from scratch
    # we could alternatively call:
    Base.metadata.create_all(bind=engine)
    # alembic.command.stamp(alembic_cfg, "head")
    # alembic.command.upgrade(alembic_cfg, "head")

    yield engine

    Base.metadata.drop_all(bind=engine)
    # alembic.command.stamp(alembic_cfg, None, purge=True)


@pytest.fixture(scope="session")
def dbsession(db_engine) -> Generator:
    yield sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


class AuthenticatedRequest:
    @property
    def is_authenticated(self):
        return True

    @property
    def identity(self):
        credentials = {
            "email": "testing_user@test.com",
            "password": "p@ss",
        }
        return User(**credentials).save()


@pytest.fixture(name="emitted_queries")
def count_database_queries(dbengine):
    """
    Return a list of the SQL statement executed by the code under test

    To be used in accordance with len() to count the number of queries
    executed
    """
    queries = []

    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        sql_t = (statement, parameters)
        if sql_t not in queries:
            queries.append(sql_t)

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        sql_t = (statement, parameters)
        if sql_t not in queries:
            queries.append(sql_t)

    event.listen(dbengine, "before_cursor_execute", before_cursor_execute)
    event.listen(dbengine, "after_cursor_execute", after_cursor_execute)

    yield queries

    event.remove(dbengine, "before_cursor_execute", before_cursor_execute)
    event.listen(dbengine, "after_cursor_execute", after_cursor_execute)


@pytest.fixture(name="trivia_match")
def create_fixture_test(dbsession):
    match = Match().save()
    first_game = Game(match_uid=match.uid, index=1).save()
    second_game = Game(match_uid=match.uid, index=2).save()
    for i, q in enumerate(TEST_1, start=1):
        if i < 3:
            new_question = Question(game_uid=first_game.uid, text=q["text"], position=i)
        else:
            new_question = Question(
                game_uid=second_game.uid, text=q["text"], position=(i - 2)
            )
        new_question.create_with_answers(q["answers"])

    yield match


@pytest.fixture
def yaml_file_handler():
    with open("codechallenge/tests/files/file.yaml", "rb") as fp:
        b64content = b64encode(fp.read()).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"
        yield b64string, "file.yaml"


@pytest.fixture
def excel_file_handler():
    with open("codechallenge/tests/files/file.xlsx", "rb") as fp:
        yield fp, "file.xlsx"
