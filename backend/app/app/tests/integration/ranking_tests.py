from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_entities.user import UserFactory
from app.domain_service.data_transfer.ranking import RankingDTO


class TestCaseRankingEndpoints:
    def t_match_rankings(self, client: TestClient, dbsession, match_dto):
        match = match_dto.save(match_dto.new())
        user_1 = UserFactory(db_session=dbsession).fetch()
        user_2 = UserFactory(db_session=dbsession).fetch()

        rank_1 = RankingDTO(session=dbsession).new(
            match_uid=match.uid, user_uid=user_1.uid, score=4.1
        )
        rank_2 = RankingDTO(session=dbsession).new(
            match_uid=match.uid, user_uid=user_2.uid, score=4.2
        )

        RankingDTO(session=dbsession).add_many([rank_1, rank_2])

        response = client.get(f"{settings.API_V1_STR}/rankings/{match.uid}")

        assert response.ok
        assert response.json()["rankings"] == [
            {
                "match": {"name": match.name, "uid": match.uid},
                "user": {"name": user_1.name, "uid": user_1.uid},
                "score": rank_1.score,
                "uid": rank_1.uid,
            },
            {
                "match": {"name": match.name, "uid": match.uid},
                "user": {"name": user_2.name, "uid": user_2.uid},
                "score": rank_2.score,
                "uid": rank_2.uid,
            },
        ]
