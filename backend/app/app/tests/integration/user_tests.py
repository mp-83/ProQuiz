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

    def t_listAllPlayersOf(self, client: TestClient):
        user_1 = self.user_dto.fetch(signed=True)
        user_2 = self.user_dto.fetch()
        user_3 = self.user_dto.fetch()
        response = client.get(f"{settings.API_V1_STR}/players")
        assert response.ok
        returned_players = response.json()["players"]

        assert returned_players[0]["uid"] == user_1.uid
        assert returned_players[0]["signed"]

        assert returned_players[1]["uid"] == user_2.uid
        assert not returned_players[1]["signed"]

        assert returned_players[2]["uid"] == user_3.uid
        assert not returned_players[2]["signed"]

    def t_listOnlySignedPlayers(self, client: TestClient):
        user_1 = self.user_dto.fetch(signed=True)
        self.user_dto.fetch()
        response = client.get(f"{settings.API_V1_STR}/players", params={"signed": True})
        assert response.ok
        assert response.json()["players"][0]["uid"] == user_1.uid
        assert response.json()["players"][0]["signed"]

    def t_listOnlyUnSignedPlayers(self, client: TestClient):
        self.user_dto.fetch(signed=True)
        user_2 = self.user_dto.fetch()
        response = client.get(
            f"{settings.API_V1_STR}/players", params={"signed": False}
        )
        assert response.ok
        assert response.json()["players"][0]["uid"] == user_2.uid
        assert not response.json()["players"][0]["signed"]

    def t_listAllPlayersOfMatch(self, client: TestClient, match_dto):
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

        user_1 = self.user_dto.fetch(signed=True)
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

        # user_1 played to first_match & second_match
        # user_2 played to first_match & second_match
        # user_3 played to first_match only
        response = client.get(f"{settings.API_V1_STR}/players/{second_match.uid}")
        assert response.ok
        assert response.json()["players"][0]["uid"] == user_1.uid
        assert response.json()["players"][0]["signed"]

        assert response.json()["players"][1]["uid"] == user_2.uid
        assert not response.json()["players"][1]["signed"]

    def t_registerSignedUser(self, client: TestClient):
        response = client.post(
            f"{settings.API_V1_STR}/players/sign",
            json={"email": "user@domain.com", "token": "01012022"},
        )
        assert response.ok
        assert response.json()["uid"] > 0
        assert response.json()["is_active"]
        assert response.json()["email"].endswith("@progame.io")
