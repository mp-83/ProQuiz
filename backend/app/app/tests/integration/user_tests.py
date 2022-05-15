import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.reaction import ReactionDTO
from app.domain_service.data_transfer.user import UserDTO


class TestCaseUser:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.reaction_dto = ReactionDTO(session=db_session)
        self.game_dto = GameDTO(session=db_session)
        self.user_dto = UserDTO(session=db_session)

    def t_list_all_players(self, client: TestClient, match_dto):
        first_match = match_dto.save(match_dto.new())
        first_game = self.game_dto.new(match_uid=first_match.uid, index=0)
        self.game_dto.save(first_game)
        second_match = match_dto.save(match_dto.new())
        second_game = self.game_dto.new(match_uid=second_match.uid, index=0)
        self.game_dto.save(second_game)
        question_1 = self.question_dto.new(text="3*3 = ", time=0, position=0)
        self.question_dto.save(question_1)

        question_2 = self.question_dto.new(text="1+1 = ", time=1, position=1)
        self.question_dto.save(question_2)

        user_1 = self.user_dto.fetch()
        user_2 = self.user_dto.fetch()
        user_3 = self.user_dto.fetch()
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=first_match,
                question=question_1,
                user=user_1,
                game_uid=first_game.uid,
            )
        )
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=first_match,
                question=question_2,
                user=user_1,
                game_uid=first_game.uid,
            )
        )
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=first_match,
                question=question_1,
                user=user_2,
                game_uid=first_game.uid,
            )
        )
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=first_match,
                question=question_1,
                user=user_3,
                game_uid=first_game.uid,
            )
        )

        self.reaction_dto.save(
            self.reaction_dto.new(
                match=second_match,
                question=question_1,
                user=user_2,
                game_uid=second_game.uid,
            )
        )
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=second_match,
                question=question_1,
                user=user_1,
                game_uid=second_game.uid,
            )
        )

        response = client.get(f"{settings.API_V1_STR}/players/{first_match.uid}")
        assert response.ok
        assert response.json()["players"] == [
            {"full_name": None, "is_active": True},
            {"full_name": None, "is_active": True},
            {"full_name": None, "is_active": True},
        ]
