import pytest
from sqlalchemy.exc import IntegrityError, InvalidRequestError


class TestCaseGameModel:
    def test_1(self, db_session, match_dto, game_dto):
        """Two games of a match cannot have the same position"""
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(game)
        with pytest.raises((IntegrityError, InvalidRequestError)):
            another_game = game_dto.new(match_uid=match.uid, index=0)
            game_dto.save(another_game)

        db_session.rollback()
