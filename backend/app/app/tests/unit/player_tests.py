from datetime import datetime, timedelta

import pytest

from app.domain_service.play import (
    GameFactory,
    PlayerStatus,
    QuestionFactory,
    SinglePlayer,
)
from app.exceptions import (
    GameError,
    GameOver,
    HuntOver,
    MatchError,
    MatchNotPlayableError,
    MatchOver,
)


@pytest.fixture
def shuffle_patch(mocker):
    yield mocker.patch(
        "app.domain_service.play.single_player.shuffle", side_effect=lambda arr: arr
    )


class TestCaseQuestionFactory:
    def test_1(self, game_dto, match_dto, question_dto, shuffle_patch):
        """
        GIVEN: two existing questions
        WHEN: next() is called twice and then previous()
        THEN: questions are shuffled before being returned
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid, order=False)
        game_dto.save(game)
        first = question_dto.new(text="Where is Paris?", game_uid=game.uid, position=0)
        question_dto.save(first)
        second = question_dto.new(
            text="Where is London?", game_uid=game.uid, position=1
        )
        question_dto.save(second)

        question_factory = QuestionFactory(game, *())
        assert question_factory.next() == first
        assert question_factory.next() == second
        assert shuffle_patch.call_count == 2
        assert question_factory.previous() == first

    def test_2(self, match_dto, game_dto):
        """
        GIVEN: one match with game without
        WHEN: next() is called
        THEN: GameOver is raised
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)

        question_factory = QuestionFactory(game, *())
        with pytest.raises(GameOver):
            question_factory.next()

    def test_3(self, match_dto, game_dto, question_dto):
        """
        GIVEN: one match with game with one question
        WHEN: next() is called twice
        THEN: GameOver is raised after the second time
                because there are no more questions
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=0
        )
        question_dto.save(question)

        question_factory = QuestionFactory(game, *())
        question_factory.next()
        assert question_factory.is_last_question
        with pytest.raises(GameOver):
            question_factory.next()

    def test_4(self, match_dto, game_dto, question_dto):
        """
        GIVEN: a match with one game with one question
        WHEN: previous() is called without next() never called before
        THEN: GameError is raised
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is Amsterdam?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(question)
        question = question_dto.new(
            text="Where is Lion?", game_uid=game.uid, position=1
        )
        question_dto.save(question)

        question_factory = QuestionFactory(game)
        with pytest.raises(GameError):
            question_factory.previous()

    def test_5(self, match_dto, game_dto, question_dto):
        """
        GIVEN: a match with one game with one question
        WHEN: previous() is called after next() is called once
        THEN: GameError is raised
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is Amsterdam?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(question)
        question = question_dto.new(
            text="Where is Lion?", game_uid=game.uid, position=1
        )
        question_dto.save(question)

        question_factory = QuestionFactory(game)
        question_factory.next()
        with pytest.raises(GameError):
            question_factory.previous()


class TestCaseGameFactory:
    def test_1(self, match_dto, game_dto):
        """
        GIVEN: a match with three games
        WHEN: next() game is called
        THEN: games are returned based on their position (index - ascending)
        """
        match = match_dto.save(match_dto.new(order=True))
        second = game_dto.new(match_uid=match.uid, index=1)
        game_dto.save(second)
        first = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(first)
        third = game_dto.new(match_uid=match.uid, index=2)
        game_dto.save(third)

        game_factory = GameFactory(match, *())
        assert game_factory.next() == first
        assert game_factory.next() == second
        assert game_factory.next() == third

    def test_2(self, db_session, match_dto):
        """
        GIVEN: a match without games
        WHEN: next() is called
        THEN: a MatchOver is expected to be raised
        """
        match = match_dto.save(match_dto.new())
        game_factory = GameFactory(match, *())

        with pytest.raises(MatchOver):
            game_factory.next()

        db_session.rollback()

    def test_3(self, match_dto, game_dto):
        """
        GIVEN: a match with one game
        WHEN: next() was not called
        THEN: the match should not be considered as started
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        game_factory = GameFactory(match, *())

        assert not game_factory.match_started

    def test_4(self, match_dto, game_dto):
        """
        GIVEN: a match with two games
        WHEN: next() is called after one game was already played
                (mimics what happens over two separate HTTP requests)
        THEN: the second should be considered as the last game
        """
        match = match_dto.save(match_dto.new())
        g1 = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(g1)
        g2 = game_dto.new(match_uid=match.uid, index=1)
        game_dto.save(g2)
        game_factory = GameFactory(match, g1.uid)

        assert game_factory.next() == g2
        assert game_factory.is_last_game

    def test_5(self, match_dto, game_dto):
        """
        GIVEN: a match with two games
        WHEN: next() is called (there is already one game played)
        THEN: calling previous() should return the first game
        """
        match = match_dto.save(match_dto.new())
        g1 = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(g1)
        g2 = game_dto.new(match_uid=match.uid, index=1)
        game_dto.save(g2)
        game_factory = GameFactory(match, g1.uid)

        game_factory.next()
        assert game_factory.previous() == g1


class TestCaseStatus:
    def test_1(
        self, db_session, match_dto, game_dto, reaction_dto, question_dto, user_dto
    ):
        """
        GIVEN: a user that played to two matches
        WHEN: when his Status for one match is restored
        THEN: the questions_displayed() should be only those of that match
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        q1 = question_dto.new(text="Where is Miami", position=0, game=game)
        question_dto.save(q1)
        q2 = question_dto.new(text="Where is London", position=1, game=game)
        question_dto.save(q2)
        q3 = question_dto.new(text="Where is Paris", position=2, game=game)
        question_dto.save(q3)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

        first_reaction = reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=game.uid,
            )
        )
        attempt_uid = first_reaction.attempt_uid
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=game.uid,
                attempt_uid=attempt_uid,
            )
        )

        another_match = match_dto.save(match_dto.new())
        reaction_dto.save(
            reaction_dto.new(
                match=another_match,
                question=q3,
                user=user,
                game_uid=game.uid,
                attempt_uid=attempt_uid,
            )
        )
        status = PlayerStatus(user, match, db_session=db_session)
        status.current_attempt_uid = attempt_uid
        assert status.questions_displayed() == {q2.uid: q2, q1.uid: q1}

    def test_2(
        self, db_session, match_dto, game_dto, reaction_dto, question_dto, user_dto
    ):
        """
        GIVEN: a user that played a whole match with two games
        WHEN: the questions_displayed_by_game() is queried
        THEN: only the questions belonging to that game should be returned
        """
        match = match_dto.save(match_dto.new())
        first_game = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(first_game)
        q1 = question_dto.new(text="Where is Miami", position=0, game=first_game)
        question_dto.save(q1)
        q2 = question_dto.new(text="Where is London", position=1, game=first_game)
        question_dto.save(q2)
        second_game = game_dto.new(match_uid=match.uid, index=1)
        game_dto.save(second_game)
        q3 = question_dto.new(text="Where is Paris", position=2, game=second_game)
        question_dto.save(q3)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

        first_reaction = reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=first_game.uid,
            )
        )
        attempt_uid = first_reaction.attempt_uid
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=first_game.uid,
                attempt_uid=attempt_uid,
            )
        )
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q3,
                user=user,
                game_uid=second_game.uid,
            )
        )
        status = PlayerStatus(user, match, db_session=db_session)
        status.current_attempt_uid = attempt_uid
        assert status.questions_displayed_by_game(first_game) == {
            q2.uid: q2,
            q1.uid: q1,
        }

    def test_3(
        self, db_session, match_dto, game_dto, reaction_dto, question_dto, user_dto
    ):
        """
        GIVEN: a match with two games, with 1 and 2 questions respectively,
                and a user who reacted to the first two questions
        WHEN: the all_games_played() is queried
        THEN: only the first game should considered as completed since the second
                question of the second game was not displayed
        """
        match = match_dto.save(match_dto.new())
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
        first_reaction = reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
            )
        )
        attempt_uid = first_reaction.attempt_uid
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=g2.uid,
                attempt_uid=attempt_uid,
            )
        )

        status = PlayerStatus(user, match, db_session=db_session)
        status.current_attempt_uid = attempt_uid
        assert status.all_games_played() == {g1.uid: g1}

    def test_4(
        self, db_session, match_dto, game_dto, reaction_dto, question_dto, user_dto
    ):
        """
        GIVEN: a two games match, each game with one question
        WHEN: the user `reacts` to all questions
        THEN: the match should be considered as completed because
                there are 2 reactions with the same attempt_uid and
                both games considered as played
        """
        match = match_dto.save(match_dto.new())
        g1 = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(g1)
        g2 = game_dto.new(match_uid=match.uid, index=1)
        game_dto.save(g2)
        q1 = question_dto.new(text="Where is Miami", position=0, game=g1)
        question_dto.save(q1)
        q2 = question_dto.new(text="Where is London", position=0, game=g2)
        question_dto.save(q2)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        status = PlayerStatus(user, match, db_session=db_session)
        first_reaction = reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
            )
        )
        status.current_attempt_uid = first_reaction.attempt_uid
        assert status.questions_displayed() == {q1.uid: q1}
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=g2.uid,
                attempt_uid=first_reaction.attempt_uid,
            )
        )

        assert status.match_completed()
        assert not status.start_fresh_one()
        assert status.questions_displayed() == {q1.uid: q1, q2.uid: q2}

    def test_5(
        self, db_session, match_dto, game_dto, reaction_dto, question_dto, user_dto
    ):
        """
        GIVEN: a match with two questions, that can be played 3 times
        WHEN: the user `reacts` to the first question 2 times
        THEN: the match can't be considered completed because, no
                attempt was completed (i.e. there are no 2 reactions
                with the same attempt_uid) and only the first question
                was displayed both times
        """
        match = match_dto.save(match_dto.new(times=3))
        g1 = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(g1)
        q1 = question_dto.new(text="Where is Miami", position=0, game=g1)
        question_dto.save(q1)
        q2 = question_dto.new(text="Where is London", position=1, game=g1)
        question_dto.save(q2)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
            )
        )
        another_reaction = reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
            )
        )
        attempt_uid = another_reaction.attempt_uid
        status = PlayerStatus(user, match, db_session=db_session)
        status.current_attempt_uid = attempt_uid

        assert not status.match_completed()
        assert status.start_fresh_one()
        assert status.questions_displayed() == {q1.uid: q1}

    def test_6(
        self, db_session, match_dto, game_dto, reaction_dto, question_dto, user_dto
    ):
        """
        verify several context related properties with a fresh empty match
        """
        match = match_dto.save(match_dto.new())
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        status = PlayerStatus(user, match, db_session=db_session)
        assert status.start_fresh_one()
        assert status.questions_displayed() == {}
        assert status.all_games_played() == {}

    def test_7(
        self, db_session, match_dto, game_dto, reaction_dto, question_dto, user_dto
    ):
        """
        GIVEN: a match with two games and 3 questions
        WHEN: the user completes the match
        THEN: all_games_played() returns both games and the
                total score is computed
        """
        match = match_dto.save(match_dto.new())
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
        first_reaction = reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
                score=3,
            )
        )
        attempt_uid = first_reaction.attempt_uid
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=g2.uid,
                attempt_uid=attempt_uid,
                score=2.4,
            )
        )
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=q3,
                user=user,
                game_uid=g2.uid,
                attempt_uid=attempt_uid,
                score=None,
            )
        )

        status = PlayerStatus(user, match, db_session=db_session)
        status.current_attempt_uid = attempt_uid
        assert status.current_score() == 5.4
        assert status.all_games_played() == {g1.uid: g1, g2.uid: g2}


class TestCaseSinglePlayer:
    def test_1(self, db_session, match_dto, game_dto, question_dto, user_dto):
        """
        GIVEN: a match with one game and one questions
        WHEN: the users starts the match
        THEN: a new reaction is immediately created
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(question)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        question_returned, _ = player.start()

        assert question_returned == question
        assert player.current == question_returned
        assert user.reactions.count() == 1

    def test_2(
        self, db_session, match_dto, game_dto, question_dto, user_dto, answer_dto
    ):
        """
        GIVEN: a match with one question only
        WHEN: the user reacts to it
        THEN: the answer is correct because was the only
        one and it was at position 0, and forward() returns
        the second question as expected
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        first_question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(first_question)
        answer = answer_dto.new(question=first_question, text="UK", position=0)
        answer_dto.save(answer)
        second_question = question_dto.new(
            text="Where is Paris?",
            game_uid=game.uid,
            position=1,
        )
        question_dto.save(second_question)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        player.start()
        was_correct = player.react(first_question, answer)
        assert user.reactions.count() > 0
        assert player.forward() == second_question
        assert was_correct

    def test_3(self, db_session, match_dto, game_dto, question_dto, user_dto):
        """
        GIVEN: a match is expired
        WHEN: then user starts it
        THEN: a MatchError should be raised
        """
        match = match_dto.new(to_time=datetime.now() - timedelta(microseconds=10))
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(question)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        with pytest.raises(MatchError) as e:
            player.start()

        assert e.value.message == "Expired match"

    def test_4(
        self, db_session, match_dto, game_dto, question_dto, user_dto, answer_dto
    ):
        """
        GIVEN: a match that can be played two times
        WHEN: the user plays once
        THEN: the method `start_fresh_one` should return True
        """
        match = match_dto.save(match_dto.new(times=2))
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        first_question = question_dto.new(
            text="Where is Graz?", game_uid=game.uid, position=0
        )
        question_dto.save(first_question)
        first_answer = answer_dto.new(
            question=first_question, text="Austria", position=1, level=2
        )

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        returned_question, attempt_uid = player.start()
        status.current_attempt_uid = attempt_uid
        assert returned_question == first_question
        player.react(first_question, first_answer)
        with pytest.raises(MatchOver):
            player.forward()

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        assert status.start_fresh_one()
        player.start()

        db_session.rollback()

    def test_5(
        self, db_session, match_dto, game_dto, question_dto, user_dto, answer_dto
    ):
        """
        GIVEN: a match that can be played 2 times
        WHEN: the user attempts to play it a third time
        THEN: `start_fresh_one()` should return True two times
                and at the third attempt a MatchNotPlayableError
                should be raised
        """
        max_times = 2
        match = match_dto.save(match_dto.new(times=max_times))
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        first_question = question_dto.new(
            text="Where is Graz?", game_uid=game.uid, position=0
        )
        question_dto.save(first_question)
        first_answer = answer_dto.new(
            question=first_question, text="Austria", position=1, level=2
        )

        for _ in range(max_times):
            status = PlayerStatus(user, match, db_session=db_session)
            player = SinglePlayer(status, user, match, db_session=db_session)
            assert status.start_fresh_one()
            next_question, attempt_uid = player.start()
            status.current_attempt_uid = attempt_uid
            assert next_question == first_question
            player.react(first_question, first_answer)
            with pytest.raises(MatchOver):
                player.forward()

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        with pytest.raises(MatchNotPlayableError):
            player.start()

        db_session.rollback()

    def test_6(
        self,
        db_session,
        match_dto,
        game_dto,
        question_dto,
        user_dto,
        reaction_dto,
        open_answer_dto,
    ):
        """
        GIVEN: a user that has answered one of the two open questions
        WHEN: he answers also the second question
        THEN: the match should be considered completed, with 2 reactions
                for the user
        """
        match = match_dto.save(match_dto.new())
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        first_question = question_dto.new(
            text="Where is Graz?", game_uid=game.uid, position=0
        )
        question_dto.save(first_question)
        second_question = question_dto.new(
            text="Where is Istanbul?",
            game_uid=game.uid,
            position=1,
        )
        question_dto.save(second_question)
        open_answer_1 = open_answer_dto.new(text="Austria")
        open_answer_dto.save(open_answer_1)

        first_reaction = reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=first_question,
                user=user,
                game_uid=game.uid,
                open_answer_uid=open_answer_1.uid,
                score=None,
            )
        )

        open_answer_2 = open_answer_dto.new(text="Turkey")
        open_answer_dto.save(open_answer_2)

        status = PlayerStatus(user, match, db_session=db_session)
        status.current_attempt_uid = first_reaction.attempt_uid
        player = SinglePlayer(status, user, match, db_session=db_session)
        was_correct = player.react(second_question, open_answer=open_answer_2)
        with pytest.raises(MatchOver):
            player.forward()

        assert user.reactions.count() == 2
        assert not was_correct

    def test_7(
        self, db_session, match_dto, game_dto, question_dto, user_dto, answer_dto
    ):
        """
        GIVEN: a treasure-hunt match, which is only
        WHEN: the user answers wrongly
        THEN: a HuntOver exception should be raised
        """
        match = match_dto.save(match_dto.new(treasure_hunt=True))
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        first_question = question_dto.new(
            text="Where is Graz?", game_uid=game.uid, position=0
        )
        question_dto.save(first_question)
        correct = answer_dto.new(
            question_uid=first_question.uid, text="Austria", position=1, level=2
        )
        answer_dto.save(correct)
        wrong = answer_dto.new(
            question_uid=first_question.uid, text="Germany", position=2, level=2
        )
        answer_dto.save(wrong)
        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        with pytest.raises(HuntOver):
            player.react(first_question, wrong)
