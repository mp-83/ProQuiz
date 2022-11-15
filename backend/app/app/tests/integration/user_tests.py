from fastapi.testclient import TestClient

from app.core.config import settings


class TestCaseUser:
    def test_1(self, client: TestClient, user_dto):
        """listing all existing players without filters"""
        user_1 = user_dto.fetch(signed=True)
        user_2 = user_dto.fetch()
        user_3 = user_dto.fetch()
        response = client.get(f"{settings.API_V1_STR}/players")
        assert response.ok
        returned_players = response.json()["players"]

        assert returned_players[0]["uid"] == user_1.uid
        assert returned_players[0]["signed"]

        assert returned_players[1]["uid"] == user_2.uid
        assert not returned_players[1]["signed"]

        assert returned_players[2]["uid"] == user_3.uid
        assert not returned_players[2]["signed"]

    def test_2(self, client: TestClient, user_dto):
        """listing only signed users"""
        user_1 = user_dto.fetch(signed=True)
        user_dto.fetch()
        response = client.get(f"{settings.API_V1_STR}/players", params={"signed": True})
        assert response.ok
        assert response.json()["players"][0]["uid"] == user_1.uid
        assert response.json()["players"][0]["signed"]

    def test_3(self, client: TestClient, user_dto):
        """listing only unsigned players"""
        user_dto.fetch(signed=True)
        user_2 = user_dto.fetch()
        response = client.get(
            f"{settings.API_V1_STR}/players", params={"signed": False}
        )
        assert response.ok
        assert response.json()["players"][0]["uid"] == user_2.uid
        assert not response.json()["players"][0]["signed"]

    def test_4(
        self,
        client: TestClient,
        match_dto,
        game_dto,
        question_dto,
        user_dto,
        reaction_dto,
    ):
        """
        GIVEN: three users who played to a subset of the existing match
                user_1 played to first_match & second_match
                user_2 played to first_match & second_match
                user_3 played to first_match only
        WHEN: the call is made passing the match parameter
        THEN: only the players that played to that match should be returned
        """
        first_match = match_dto.save(match_dto.new())
        first_game = game_dto.new(match_uid=first_match.uid, index=0)
        game_dto.save(first_game)
        second_match = match_dto.save(match_dto.new())
        second_game = game_dto.new(match_uid=second_match.uid, index=0)
        game_dto.save(second_game)
        question_1 = question_dto.new(text="3*3 = ", time=0, position=0)
        question_dto.save(question_1)

        question_2 = question_dto.new(text="1+1 = ", time=1, position=1)
        question_dto.save(question_2)

        user_1 = user_dto.fetch(signed=True)
        user_2 = user_dto.fetch()
        user_3 = user_dto.fetch()
        reaction_dto.save(
            reaction_dto.new(
                match=first_match,
                question=question_1,
                user=user_1,
                game_uid=first_game.uid,
            )
        )
        reaction_dto.save(
            reaction_dto.new(
                match=first_match,
                question=question_2,
                user=user_1,
                game_uid=first_game.uid,
            )
        )
        reaction_dto.save(
            reaction_dto.new(
                match=first_match,
                question=question_1,
                user=user_2,
                game_uid=first_game.uid,
            )
        )
        reaction_dto.save(
            reaction_dto.new(
                match=first_match,
                question=question_1,
                user=user_3,
                game_uid=first_game.uid,
            )
        )

        reaction_dto.save(
            reaction_dto.new(
                match=second_match,
                question=question_1,
                user=user_2,
                game_uid=second_game.uid,
            )
        )
        reaction_dto.save(
            reaction_dto.new(
                match=second_match,
                question=question_1,
                user=user_1,
                game_uid=second_game.uid,
            )
        )

        response = client.get(f"{settings.API_V1_STR}/players/{second_match.uid}")
        assert response.ok
        assert response.json()["players"][0]["uid"] == user_1.uid
        assert response.json()["players"][0]["signed"]

        assert response.json()["players"][1]["uid"] == user_2.uid
        assert not response.json()["players"][1]["signed"]

    def test_5(self, client: TestClient):
        """Register a new `signed` user"""
        response = client.post(
            f"{settings.API_V1_STR}/players/sign",
            json={"email": "user@domain.com", "token": "01012022"},
        )
        assert response.ok
        assert response.json()["uid"] > 0
        assert response.json()["is_active"]
        assert response.json()["email"].endswith("@progame.io")
