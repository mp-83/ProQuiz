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
            food_match = self.match_dto.new(name=name)
            self.match_dto.save(food_match)
            content = self.parse_yaml_content("/app/quizzes/quiz_food.1.yaml")
            self.match_dto.insert_questions(food_match, content["questions"])

    def create_general_match(self):
        name = "General quiz"
        food_match = self.match_dto.get(name=name)
        if not food_match:
            logger.info(f"Creating match: {name}")
            food_match = self.match_dto.new(name=name)
            self.match_dto.save(food_match)
            content = self.parse_yaml_content("/app/quizzes/quiz_gen.1.yaml")
            self.match_dto.insert_questions(food_match, content["questions"])

    def create_geography_matches(self):
        name = "GEO quiz"
        geo_match = self.match_dto.get(name=name)
        if not geo_match:
            logger.info(f"Creating match: {name}")
            geo_match = self.match_dto.new(name=name)
            self.match_dto.save(geo_match)
            for fname in [
                "quiz_geo.1.yaml",
                "quiz_geo.2.yaml",
                "quiz_geo.3.yaml",
                "quiz_geo.6.yaml",
            ]:
                content = self.parse_yaml_content(f"/app/quizzes/{fname}")
                self.match_dto.insert_questions(geo_match, content["questions"])

        name = "Brief GEO quiz.1"
        geo_match = self.match_dto.get(name=name)
        if not geo_match:
            logger.info(f"Creating match: {name}")
            geo_match = self.match_dto.new(name=name)
            self.match_dto.save(geo_match)
            content = self.parse_yaml_content("/app/quizzes/quiz_geo.4.yaml")
            self.match_dto.insert_questions(geo_match, content["questions"])

        name = "Brief GEO quiz.2"
        geo_match = self.match_dto.get(name=name)
        if not geo_match:
            logger.info(f"Creating match: {name}")
            geo_match = self.match_dto.new(name=name)
            self.match_dto.save(geo_match)
            for fname in ["quiz_geo.5.yaml", "quiz_geo.6.yaml"]:
                content = self.parse_yaml_content(f"/app/quizzes/{fname}")
                self.match_dto.insert_questions(geo_match, content["questions"])

    def create_history_matches(self):
        name = "History quiz.1"
        history_match_1 = self.match_dto.get(name=name)
        if not history_match_1:
            logger.info(f"Creating match: {name}")
            history_match_1 = self.match_dto.new(name=name)
            self.match_dto.save(history_match_1)
            content = self.parse_yaml_content("/app/quizzes/quiz_history.1.yaml")
            self.match_dto.insert_questions(history_match_1, content["questions"])

        name = "History quiz.2"
        history_match_2 = self.match_dto.get(name=name)
        if not history_match_2:
            logger.info(f"Creating match: {name}")
            history_match_2 = self.match_dto.new(name=name)
            self.match_dto.save(history_match_2)
            content = self.parse_yaml_content("/app/quizzes/quiz_history.2.yaml")
            self.match_dto.insert_questions(history_match_2, content["questions"])

    def create_music_match(self):
        name = "Music quiz.1"
        music_match = self.match_dto.get(name=name)
        if not music_match:
            logger.info(f"Creating match: {name}")
            music_match = self.match_dto.new(name=name)
            self.match_dto.save(music_match)
            content = self.parse_yaml_content("/app/quizzes/quiz_music.yaml")
            self.match_dto.insert_questions(music_match, content["questions"])

    def create_boolean_matches(self):
        name = "Boolean quiz.1"
        boolean_match_1 = self.match_dto.get(name=name)
        if not boolean_match_1:
            logger.info(f"Creating match: {name}")
            boolean_match_1 = self.match_dto.new(name=name)
            self.match_dto.save(boolean_match_1)
            content = self.parse_yaml_content("/app/quizzes/quiz_bool.1.yaml")
            self.match_dto.insert_questions(boolean_match_1, content["questions"])

        name = "Boolean quiz.2"
        boolean_match_2 = self.match_dto.get(name=name)
        if not boolean_match_2:
            logger.info(f"Creating match: {name}")
            boolean_match_2 = self.match_dto.new(name=name)
            self.match_dto.save(boolean_match_2)
            content = self.parse_yaml_content("/app/quizzes/quiz_bool.1.yaml")
            self.match_dto.insert_questions(boolean_match_2, content["questions"])

    def prefill(self):
        self.create_first_match()
        self.create_general_match()
        self.create_geography_matches()
        self.create_history_matches()
        self.create_music_match()
        self.create_boolean_matches()


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
