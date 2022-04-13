from app.entities import Game, Match, Question, Reaction
from app.entities.user import UserFactory


class TestCaseUser:
    def t_list_all_players(self, testapp):
        first_match = Match().save()
        first_game = Game(match_uid=first_match.uid, index=0).save()
        second_match = Match().save()
        second_game = Game(match_uid=second_match.uid, index=0).save()
        question_1 = Question(text="3*3 = ", time=0, position=0).save()
        question_2 = Question(text="1+1 = ", time=1, position=1).save()

        user_1 = UserFactory().fetch()
        user_2 = UserFactory().fetch()
        user_3 = UserFactory().fetch()
        Reaction(
            match=first_match, question=question_1, user=user_1, game_uid=first_game.uid
        ).save()
        Reaction(
            match=first_match, question=question_2, user=user_1, game_uid=first_game.uid
        ).save()
        Reaction(
            match=first_match, question=question_1, user=user_2, game_uid=first_game.uid
        ).save()
        Reaction(
            match=first_match, question=question_1, user=user_3, game_uid=first_game.uid
        ).save()

        Reaction(
            match=second_match,
            question=question_1,
            user=user_2,
            game_uid=second_game.uid,
        ).save()
        Reaction(
            match=second_match,
            question=question_1,
            user=user_1,
            game_uid=second_game.uid,
        ).save()

        response = testapp.get("/players", {"match_uid": first_match.uid}, status=200)
        assert len(response.json["players"]) == 3
