import os
from base64 import b64encode
from datetime import timedelta
from typing import Dict, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.core import security
from app.core.config import settings
from app.domain_entities.db.base import Base
from app.domain_entities.db.session import get_db
from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.open_answer import OpenAnswerDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.reaction import ReactionDTO
from app.domain_service.data_transfer.user import UserDTO
from app.main import app
from app.tests.fixtures import TEST_1
from app.tests.utilities.user import authentication_token_from_email

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def init_db():
    Base.metadata.create_all(bind=test_engine)


def reset_db():
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    yield session_factory()


def override_get_current_user():
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = session_factory()
    yield UserDTO(session=session).get(uid=1)


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture()
def old_db_session() -> Generator:
    # alembic_cfg = alembic.config.Config(alembic_ini_file)
    # alembic.command.stamp(alembic_cfg, None, purge=True)

    # run migrations to initialize the database
    # depending on how we want to initialize the database from scratch
    # we could alternatively call:
    # alembic.command.stamp(alembic_cfg, "head")
    # alembic.command.upgrade(alembic_cfg, "head")
    # alembic.command.stamp(alembic_cfg, None, purge=True)
    yield


@pytest.fixture()
def db_session() -> Session:
    init_db()
    _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    yield _session_factory()
    reset_db()


@pytest.fixture()
def client(db_session) -> Generator:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def access_token_expires():
    return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


@pytest.fixture(scope="module")
def superuser_token_headers(access_token_expires) -> Dict[str, str]:
    a_token = {
        "access_token": security.create_access_token(
            1, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
    return {"Authorization": f"Bearer {a_token}"}


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> Dict[str, str]:
    # performs the whole authentication process
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )


class Cookie:
    def values(self):
        return []


def pytest_addoption(parser):
    parser.addoption("--ini", action="store", metavar="INI_FILE")


@pytest.fixture(scope="session")
def ini_file(request):
    # potentially grab this path from a pytest option
    return os.path.abspath("pytest.ini")


@pytest.fixture(scope="session")
def alembic_ini_file(request):
    return os.path.abspath("alembic.ini")


class AuthenticatedRequest:
    @property
    def is_authenticated(self):
        return True


@pytest.fixture(name="emitted_queries")
def count_database_queries():
    """
    Return a list of the SQL statement executed by the code under test

    To be used in accordance with len() to count the number of queries
    executed
    """
    queries = []
    _engine = test_engine

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

    event.listen(_engine, "before_cursor_execute", before_cursor_execute)
    event.listen(_engine, "after_cursor_execute", after_cursor_execute)

    yield queries

    event.remove(_engine, "before_cursor_execute", before_cursor_execute)
    event.listen(_engine, "after_cursor_execute", after_cursor_execute)


@pytest.fixture
def match_dto(db_session):
    yield MatchDTO(session=db_session)


@pytest.fixture
def game_dto(db_session):
    yield GameDTO(session=db_session)


@pytest.fixture
def question_dto(db_session):
    yield QuestionDTO(session=db_session)


@pytest.fixture
def user_dto(db_session) -> UserDTO:
    return UserDTO(session=db_session)


@pytest.fixture
def answer_dto(db_session):
    return AnswerDTO(session=db_session)


@pytest.fixture
def open_answer_dto(db_session):
    return OpenAnswerDTO(session=db_session)


@pytest.fixture
def reaction_dto(db_session):
    return ReactionDTO(session=db_session)


@pytest.fixture(name="trivia_match")
def create_fixture_test(db_session, match_dto, game_dto, question_dto):
    match = match_dto.save(match_dto.new())

    first_game = game_dto.new(match_uid=match.uid, index=1)
    game_dto.save(first_game)
    second_game = game_dto.new(match_uid=match.uid, index=2)
    game_dto.save(second_game)
    for i, question_dict in enumerate(TEST_1, start=1):
        if i < 3:
            new_question = question_dto.new(
                game_uid=first_game.uid,
                text=question_dict["text"],
                position=i,
            )
        else:
            new_question = question_dto.new(
                game_uid=second_game.uid,
                text=question_dict["text"],
                position=(i - 2),
            )
        question_dto.create_with_answers(new_question, question_dict["answers"])

    yield match


@pytest.fixture
def yaml_file_handler():
    with open("app/tests/files/file.yaml", "rb") as fp:
        b64content = b64encode(fp.read()).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"
        yield b64string, "file.yaml"


@pytest.fixture
def excel_file_handler():
    with open("app/tests/files/file.xlsx", "rb") as fp:
        yield fp, "file.xlsx"
