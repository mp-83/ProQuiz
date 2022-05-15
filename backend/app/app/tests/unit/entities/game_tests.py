import pytest
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO


class TestCaseGameModel:
    @pytest.fixture(autouse=True)
    def setUp(self, dbsession):
        self.question_dto = QuestionDTO(session=dbsession)
        self.match_dto = MatchDTO(session=dbsession)
        self.game_dto = GameDTO(session=dbsession)

    def t_raiseErrorWhenTwoGamesOfMatchHaveSamePosition(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        with pytest.raises((IntegrityError, InvalidRequestError)):
            another_game = self.game_dto.new(match_uid=match.uid, index=1)
            self.game_dto.save(another_game)

        dbsession.rollback()

    def t_orderedQuestionsMethod(self, dbsession, emitted_queries):
        # Questions are intentionally created unordered
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        question_2 = self.question_dto.new(
            text="Where is London?", game_uid=game.uid, position=1
        )
        self.question_dto.save(question_2)
        question_1 = self.question_dto.new(
            text="Where is Lisboa?", game_uid=game.uid, position=0
        )
        self.question_dto.save(question_1)
        question_4 = self.question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=3
        )
        self.question_dto.save(question_4)
        question_3 = self.question_dto.new(
            text="Where is Berlin?", game_uid=game.uid, position=2
        )
        self.question_dto.save(question_3)

        assert len(emitted_queries) == 9
        assert game.ordered_questions[0] == question_1
        assert game.ordered_questions[1] == question_2
        assert game.ordered_questions[2] == question_3
        assert game.ordered_questions[3] == question_4
        assert len(emitted_queries) == 10
