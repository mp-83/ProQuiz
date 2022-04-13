from app.entities import Match, Ranking
from app.entities.user import UserFactory


class TestCaseRankingEndpoints:
    def t_match_rankings(self, testapp):
        match = Match().save()
        user_1 = UserFactory().fetch()
        user_2 = UserFactory().fetch()
        Ranking(match_uid=match.uid, user_uid=user_1.uid, score=4.1).save(),
        Ranking(match_uid=match.uid, user_uid=user_2.uid, score=4.2).save()
        response = testapp.get("/rankings", {"match_uid": match.uid}, status=200)
        assert response.json["rankings"] == [
            {
                "match": {"name": match.name, "uid": match.uid},
                "user": {"name": user_1.name},
            },
            {
                "match": {"name": match.name, "uid": match.uid},
                "user": {"name": user_2.name},
            },
        ]

    def t_match_uid_required(self, testapp):
        testapp.get("/rankings", {}, status=400)
