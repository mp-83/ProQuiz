from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_entities import Game, Match, Question, Reaction
from app.domain_entities.user import UserFactory


class TestCaseUser:
    def t_list_all_players(self, client: TestClient, dbsession):
        first_match = Match(db_session=dbsession).save()
        first_game = Game(
            match_uid=first_match.uid, index=0, db_session=dbsession
        ).save()
        second_match = Match(db_session=dbsession).save()
        second_game = Game(
            match_uid=second_match.uid, index=0, db_session=dbsession
        ).save()
        question_1 = Question(
            text="3*3 = ", time=0, position=0, db_session=dbsession
        ).save()
        question_2 = Question(
            text="1+1 = ", time=1, position=1, db_session=dbsession
        ).save()

        user_1 = UserFactory(db_session=dbsession).fetch()
        user_2 = UserFactory(db_session=dbsession).fetch()
        user_3 = UserFactory(db_session=dbsession).fetch()
        Reaction(
            match=first_match,
            question=question_1,
            user=user_1,
            game_uid=first_game.uid,
            db_session=dbsession,
        ).save()
        Reaction(
            match=first_match,
            question=question_2,
            user=user_1,
            game_uid=first_game.uid,
            db_session=dbsession,
        ).save()
        Reaction(
            match=first_match,
            question=question_1,
            user=user_2,
            game_uid=first_game.uid,
            db_session=dbsession,
        ).save()
        Reaction(
            match=first_match,
            question=question_1,
            user=user_3,
            game_uid=first_game.uid,
            db_session=dbsession,
        ).save()

        Reaction(
            match=second_match,
            question=question_1,
            user=user_2,
            game_uid=second_game.uid,
            db_session=dbsession,
        ).save()
        Reaction(
            match=second_match,
            question=question_1,
            user=user_1,
            game_uid=second_game.uid,
            db_session=dbsession,
        ).save()

        response = client.get(f"{settings.API_V1_STR}/players/{first_match.uid}")
        assert response.ok
        assert response.json()["players"] == [
            {"full_name": None, "is_active": True},
            {"full_name": None, "is_active": True},
            {"full_name": None, "is_active": True},
        ]
