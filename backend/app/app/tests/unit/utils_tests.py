from datetime import datetime, timedelta

import pytest

from app.domain_entities.db.utils import QAppenderClass
from app.domain_service.data_transfer.game import Game
from app.domain_service.data_transfer.reaction import Reaction


class TestCaseBaseQueryAppender:
    @pytest.fixture
    def test_data(
        self, db_session, match_dto, game_dto, reaction_dto, question_dto, user_dto
    ):
        match = match_dto.new(with_code=True)
        match_dto.save(match)
        g1 = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(g1)
        g2 = game_dto.new(match_uid=match.uid, index=1)
        game_dto.save(g2)

        q1 = question_dto.new(text="Where is Miami", position=0, game=g1)
        question_dto.save(q1)
        q2 = question_dto.new(text="Where is London", position=0, game=g2)
        question_dto.save(q2)
        q3 = question_dto.new(text="Where is Montreal", position=1, game=g2)
        question_dto.save(q3)

        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
                score=3,
            )
        )
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                answer_time=datetime.now(),
                game_uid=g2.uid,
                score=2.4,
            )
        )
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q3,
                user=user,
                answer_time=datetime.now(),
                game_uid=g2.uid,
                score=None,
            )
        )
        yield match, q1, q2

    def test_1(self):
        """
        GIVEN: some input clauses
        WHEN: the verify split_clauses() method is called
        THEN: the resulting clauses are split among
                simple ones (those without operator) and
                complex ones (those with the operator suffixed
                in their initial definition)
        """
        clauses = {
            "user_id": 2,
            "answer_time__gt": "2022-01-01",
            "game_uid__notin": [1, 4],
        }
        simple, with_op = QAppenderClass(Reaction).split_clauses(**clauses)
        assert simple == {"user_id": 2}
        assert with_op == {
            "answer_time": ("__gt__", "2022-01-01"),
            "game_uid": ("notin_", [1, 4]),
        }

    def test_2(self, test_data, db_session):
        match, _, _ = test_data
        tomorrow = datetime.now() + timedelta(days=1)
        expected = (
            db_session.query(Reaction).filter(Reaction.answer_time < tomorrow).all()
        )
        result = match.reactions.filter_by(answer_time__lt=tomorrow).all()
        assert result == expected

    def test_3(self, test_data, db_session):
        match, _, _ = test_data
        expected = db_session.query(Game).filter(Game.uid.notin_([0])).all()
        result = match.games.filter_by(uid__notin=[0]).all()
        assert result == expected
