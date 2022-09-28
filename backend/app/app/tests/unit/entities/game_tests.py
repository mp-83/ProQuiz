import pytest
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO


class TestCaseGameModel:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.match_dto = MatchDTO(session=db_session)
        self.game_dto = GameDTO(session=db_session)

    def test_raiseErrorWhenTwoGamesOfMatchHaveSamePosition(self, db_session):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        with pytest.raises((IntegrityError, InvalidRequestError)):
            another_game = self.game_dto.new(match_uid=match.uid, index=0)
            self.game_dto.save(another_game)

        db_session.rollback()

    def test_orderedQuestionsMethod(self, emitted_queries):
        # Questions are intentionally created unordered
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question_1 = self.question_dto.new(
            text="Where is Lisboa?", game_uid=game.uid, position=0
        )
        self.question_dto.save(question_1)
        question_2 = self.question_dto.new(
            text="Where is London?", game_uid=game.uid, position=1
        )
        self.question_dto.save(question_2)

        question_3 = self.question_dto.new(
            text="Where is Berlin?", game_uid=game.uid, position=2
        )
        self.question_dto.save(question_3)

        question_4 = self.question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=3
        )
        self.question_dto.save(question_4)

        assert len(emitted_queries) == 9

        assert game.questions.all()[0] == question_1
        assert game.questions.all()[1] == question_2
        assert game.questions.all()[2] == question_3
        assert game.questions.all()[3] == question_4

        assert len(emitted_queries) == 10

        assert game.first_question == question_1
        assert len(emitted_queries) == 11
