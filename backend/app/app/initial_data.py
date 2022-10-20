import logging
from random import randint

import yaml
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain_entities.db.session import session_factory
from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
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
        self.game_dto = GameDTO(session=db_session)
        self.user_dto = UserDTO(session=db_session)

    def parse_fixed_match(self, fname):
        # DO REMEMBER that changes to MatchYamlImport.fixed_match_structure
        # must be manually ported here
        with open(fname, "r") as fp:
            file_content = yaml.load(fp.read(), yaml.Loader)
            result = {"questions": []}
            question = {}
            for i, elem in enumerate(file_content.get("questions"), start=1):
                if i % 3 == 1 and elem and "text" in elem:
                    question["text"] = elem["text"]
                elif i % 3 == 2 and elem and "time" in elem:
                    question["time"] = elem["time"]
                elif i % 3 == 0:
                    question["answers"] = [{"text": text} for text in elem["answers"]]
                    if question.get("text") is None:
                        question = {}
                        continue
                    result["questions"].append(question)
                    question = {}
            return result

    def parse_open_match(self, fname):
        # DO REMEMBER that changes to MatchYamlImport.open_match_structure
        # must be manually ported here
        with open(fname, "r") as fp:
            file_content = yaml.load(fp.read(), yaml.Loader)
            result = {"questions": []}
            question = {}
            for i, elem in enumerate(file_content.get("questions"), start=1):
                if i % 2 == 1 and elem and "text" in elem:
                    question["text"] = elem["text"]
                elif i % 2 == 0 and elem and "time" in elem:
                    question["time"] = elem["time"]
                    question["answers"] = []
                    result["questions"].append(question)
                    question = {}
            return result

    def create_food_match(self):
        name = "Food quiz"
        food_match = self.match_dto.get(name=name)
        if not food_match:
            food_match = self.match_dto.new(name=name, is_restricted=True, times=0)
            logger.info(
                f"Creating match: {name} :: with hash {food_match.uhash} :: restricted"
            )
            self.match_dto.save(food_match)
            content = self.parse_fixed_match("/app/quizzes/quiz_food.1.yaml")
            self.match_dto.insert_questions(food_match, content["questions"])

    def create_geography_matches(self):
        name = "GEO quiz [multi-game]"
        geo_match = self.match_dto.get(name=name)
        if not geo_match:
            geo_match = self.match_dto.new(name=name, order=False, times=0)
            logger.info(
                f"Creating multi-game match: {name} :: with-hash {geo_match.uhash} :: not-restricted"
            )
            self.match_dto.save(geo_match)
            for index, fname in enumerate(
                [
                    "quiz_geo.1.yaml",
                    "quiz_geo.2.yaml",
                    "quiz_geo.3.yaml",
                    "quiz_geo.6.yaml",
                ],
            ):
                game = self.game_dto.save(
                    self.game_dto.new(match_uid=geo_match.uid, index=index)
                )
                content = self.parse_fixed_match(f"/app/quizzes/{fname}")
                self.match_dto.insert_questions(
                    geo_match, content["questions"], game.uid
                )

        name = "Brief GEO quiz.1"
        geo_match = self.match_dto.get(name=name)
        if not geo_match:
            geo_match = self.match_dto.new(
                name=name, with_code=True, order=False, times=0
            )
            logger.info(
                f"Creating match: {name} :: with-code {geo_match.code} :: not-restricted"
            )
            self.match_dto.save(geo_match)
            content = self.parse_fixed_match("/app/quizzes/quiz_geo.4.yaml")
            self.match_dto.insert_questions(geo_match, content["questions"])

        name = "GEO quiz.2 [multi-game]"
        geo_match = self.match_dto.get(name=name)
        if not geo_match:
            geo_match = self.match_dto.new(name=name, with_code=True, times=0)
            logger.info(
                f"Creating multi-game match: {name} :: with-code {geo_match.code} :: not-restricted"
            )
            self.match_dto.save(geo_match)
            for index, fname in enumerate(["quiz_geo.5.yaml", "quiz_geo.6.yaml"]):
                game = self.game_dto.save(
                    self.game_dto.new(match_uid=geo_match.uid, index=index)
                )
                content = self.parse_fixed_match(f"/app/quizzes/{fname}")
                self.match_dto.insert_questions(
                    geo_match, content["questions"], game.uid
                )

    def create_history_matches(self):
        name = "History quiz.1"
        history_match_1 = self.match_dto.get(name=name)
        if not history_match_1:
            history_match_1 = self.match_dto.new(name=name, is_restricted=True, times=0)
            logger.info(
                f"Creating match: {name} :: with-hash {history_match_1.uhash} :: restricted"
            )
            self.match_dto.save(history_match_1)
            content = self.parse_fixed_match("/app/quizzes/quiz_history.1.yaml")
            self.match_dto.insert_questions(history_match_1, content["questions"])

        name = "History quiz.2"
        history_match_2 = self.match_dto.get(name=name)
        if not history_match_2:
            history_match_2 = self.match_dto.new(name=name, times=0)
            logger.info(
                f"Creating match: {name} :: with times questions :: with-hash {history_match_2.uhash} :: not-restricted"
            )
            self.match_dto.save(history_match_2)
            content = self.parse_fixed_match("/app/quizzes/quiz_history.2.yaml")
            for question_data in content["questions"]:
                question_data["time"] = randint(3, 10)
            self.match_dto.insert_questions(history_match_2, content["questions"])

    def create_misc_matches(self):
        name = "MISC quiz.1 [multi-game]"
        match = self.match_dto.get(name=name)
        if not match:
            match = self.match_dto.new(
                name=name, with_code=True, is_restricted=True, times=0
            )
            logger.info(
                f"Creating multi-game match: {name} :: with-hash {match.code} :: restricted"
            )
            self.match_dto.save(match)
            for index, fname in enumerate(["quiz_music.yaml", "quiz_geo.3.yaml"]):
                game = self.game_dto.save(
                    self.game_dto.new(match_uid=match.uid, index=index)
                )
                content = self.parse_fixed_match(f"/app/quizzes/{fname}")
                self.match_dto.insert_questions(match, content["questions"], game.uid)

        name = "MISC quiz.2 [multi-game]"
        match = self.match_dto.get(name=name)
        if not match:
            match = self.match_dto.new(name=name, with_code=True, times=0)
            logger.info(
                f"Creating multi-game match: {name} :: with-code {match.code} :: not-restricted"
            )
            self.match_dto.save(match)
            for index, fname in enumerate(
                ["quiz_bool.1.yaml", "quiz_geo.6.yaml", "quiz_food.1.yaml"]
            ):
                game = self.game_dto.save(
                    self.game_dto.new(match_uid=match.uid, index=index)
                )
                content = self.parse_fixed_match(f"/app/quizzes/{fname}")
                self.match_dto.insert_questions(match, content["questions"], game.uid)

    def create_boolean_matches(self):
        name = "Boolean quiz.1"
        boolean_match_1 = self.match_dto.get(name=name)
        if not boolean_match_1:
            boolean_match_1 = self.match_dto.new(
                name=name, is_restricted=True, order=False, times=0
            )
            logger.info(
                f"Creating match: {name} :: with-hash {boolean_match_1.uhash} :: restricted"
            )
            self.match_dto.save(boolean_match_1)
            content = self.parse_fixed_match("/app/quizzes/quiz_bool.1.yaml")
            self.match_dto.insert_questions(boolean_match_1, content["questions"])

        name = "Boolean quiz.2"
        boolean_match_2 = self.match_dto.get(name=name)
        if not boolean_match_2:
            boolean_match_2 = self.match_dto.new(name=name, with_code=True, times=0)
            logger.info(
                f"Creating match: {name} :: with-code {boolean_match_2.code} :: not-restricted"
            )
            self.match_dto.save(boolean_match_2)
            content = self.parse_fixed_match("/app/quizzes/quiz_bool.1.yaml")
            self.match_dto.insert_questions(boolean_match_2, content["questions"])

    def create_template_questions(self):
        content = self.parse_fixed_match("/app/quizzes/quiz_gen.1.yaml")
        logger.info(f"Creating {len(content['questions'])} template questions")

        for position, question in enumerate(content["questions"]):
            new_question = self.question_dto.new(
                text=question["text"], position=position
            )
            self.question_dto.create_with_answers(new_question, question["answers"])

    def create_open_matches(self):
        name = "Open Match 1"
        open_match_1 = self.match_dto.get(name=name)
        if not open_match_1:
            open_match_1 = self.match_dto.new(name=name, with_code=True, times=0)
            logger.info(
                f"Creating match: {name} :: with-code {open_match_1.code} :: not-restricted"
            )
            self.match_dto.save(open_match_1)
            content = self.parse_open_match("/app/quizzes/open_quiz.1.yaml")
            self.match_dto.insert_questions(open_match_1, content["questions"])

        name = "Open Match 2"
        open_match_2 = self.match_dto.get(name=name)
        if not open_match_2:
            open_match_2 = self.match_dto.new(name=name, is_restricted=True, times=0)
            logger.info(
                f"Creating match: {name} :: with-hash {open_match_2.uhash} :: restricted"
            )
            self.match_dto.save(open_match_2)
            content = self.parse_open_match("/app/quizzes/open_quiz.2.yaml")
            self.match_dto.insert_questions(open_match_2, content["questions"])

    def create_mixed_question_matches(self):
        name = "Mixed Match"
        mixed_match = self.match_dto.get(name=name)
        if not mixed_match:
            content = {
                "questions": [
                    {
                        "text": "What is going to be Daniel's new strategy, according to Mr. Miyagi?",
                        "time": 4,
                        "answers": [
                            {"text": "early retirement"},
                            {"text": "early entry into the tournament"},
                            {"text": "early training"},
                            {"text": "early sleet"},
                        ],
                    },
                    {
                        "text": "What is Johnny's punishment for losing to Daniel?",
                        "time": None,
                        "answers": [],
                    },
                    {
                        "text": "Before telling Daniel that he's the one who's going to stay in the room he's building, Miyagi tells him that it's for a what?",
                        "time": 5,
                        "answers": [
                            {"text": "refugee"},
                            {"text": "nomad"},
                            {"text": "pilgrim"},
                            {"text": "frient"},
                        ],
                    },
                    {
                        "text": "In the early part of the movie, does Mr. Miyagi think he can break a log?",
                        "time": None,
                        "answers": [],
                    },
                    {
                        "text": "Who 'sings the same tune' in front of the Shinto shrine?",
                        "time": 6,
                        "answers": [
                            {"text": "Kumiko"},
                            {"text": "Toshio"},
                            {"text": "Sato"},
                            {"text": "Ichiro"},
                        ],
                    },
                    {
                        "text": "How many days does Sato give Miyagi to mourn his father's death?",
                        "time": 10,
                        "answers": [
                            {"text": "0"},
                            {"text": "3"},
                            {"text": "1"},
                            {"text": "2"},
                        ],
                    },
                ]
            }
            mixed_match = self.match_dto.new(name=name, with_code=True, times=0)
            logger.info(
                f"Creating match: {name} :: with-hash {mixed_match.uhash} :: not-restricted"
            )
            self.match_dto.save(mixed_match)
            self.match_dto.insert_questions(mixed_match, content["questions"])

    def create_signed_user(self):
        """
        Create a set of signed users for testing purposes.

        These are also used in Locust, so every change in
        data here, must be reflected in Locust too
        """
        data = [
            ("rob@aol.com", "20081990"),
            ("alixa@gm.com", "05031950"),
            ("greg@yahoo.com", "28041980"),
            ("ross@gl.com", "11052001"),
            ("paul@mail.com", "30091995"),
        ]
        logger.info(f"Creating {len(data)} signed users")
        for email, birthday in data:
            new_user = self.user_dto.fetch(original_email=email, token=birthday)
            self.user_dto.save(new_user)

    def prefill(self):
        self.create_food_match()
        self.create_geography_matches()
        self.create_history_matches()
        self.create_misc_matches()
        self.create_boolean_matches()
        self.create_template_questions()
        self.create_open_matches()
        self.create_mixed_question_matches()
        self.create_signed_user()


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
