import logging

import yaml
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain_entities.db.session import session_factory
from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.user import UserDTO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmptyDB:
    def __init__(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.answer_dto = AnswerDTO(session=db_session)
        self.match_dto = MatchDTO(session=db_session)

    def parse_yaml_content(self, fname):
        with open(fname, "r") as fp:
            file_content = yaml.load(fp.read(), yaml.Loader)
            result = {"questions": []}
            question = {}
            for i, elem in enumerate(file_content.get("questions")):
                if i % 2 == 0:
                    question["text"] = elem
                else:
                    question["answers"] = [{"text": text} for text in elem["answers"]]
                    result["questions"].append(question)
                    question = {}

            return result

    def create_first_match(self):
        name = "Food quiz"
        food_match = self.match_dto.get(name=name)
        if not food_match:
            logger.info(f"Creating match: {name}")
            content = self.parse_yaml_content("/app/quizzes/quiz4.yaml")
            food_match = self.match_dto.new(name=name)
            self.match_dto.save(food_match)
            self.match_dto.insert_questions(food_match, content["questions"])

    def create_second_match(self):
        name = "Food quiz #2"
        food_match = self.match_dto.get(name=name)
        if not food_match:
            logger.info(f"Creating match: {name}")
            content = self.parse_yaml_content("/app/quizzes/quiz5.yaml")
            food_match = self.match_dto.new(name=name)
            self.match_dto.save(food_match)
            self.match_dto.insert_questions(food_match, content["questions"])

    def prefill(self):
        self.create_first_match()
        self.create_second_match()


# make sure all SQL Alchemy models are imported (app.db.base) before initializing DB
# otherwise, SQL Alchemy might fail to initialize relationships properly
# for more details: https://github.com/tiangolo/full-stack-fastapi-postgresql/issues/28
def populate_database(db: Session) -> None:
    dto = UserDTO(session=db)
    user = dto.get(email=settings.FIRST_SUPERUSER)
    if not user:
        logger.info(f"Creating {settings.FIRST_SUPERUSER}")
        user_in = dto.new(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_admin=True,
        )
        user = dto.save(user_in)  # noqa: F841

    EmptyDB(db).prefill()


def main() -> None:
    logger.info("Creating initial data")

    _session = session_factory()
    populate_database(_session)

    logger.info("Database is now populated")


if __name__ == "__main__":
    main()
