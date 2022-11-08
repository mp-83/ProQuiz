from datetime import datetime, timedelta

import pytest

from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.open_answer import OpenAnswerDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.ranking import RankingDTO
from app.domain_service.data_transfer.reaction import ReactionDTO
from app.domain_service.data_transfer.user import UserDTO
from app.domain_service.play import (
    GameFactory,
    PlayerStatus,
    PlayScore,
    QuestionFactory,
    SinglePlayer,
)
from app.exceptions import (
    GameError,
    GameOver,
    MatchError,
    MatchNotPlayableError,
    MatchOver,
)


@pytest.fixture
def shuffle_patch(mocker):
    yield mocker.patch(
        "app.domain_service.play.single_player.shuffle", side_effect=lambda arr: arr
    )


class TestCaseBase:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session, mocker):
        self.question_dto = QuestionDTO(session=db_session)
        self.match_dto = MatchDTO(session=db_session)
        self.reaction_dto = ReactionDTO(session=db_session)
        self.answer_dto = AnswerDTO(session=db_session)
        self.game_dto = GameDTO(session=db_session)
        self.user_dto = UserDTO(session=db_session)


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


class TestCaseStatus(TestCaseBase):
    def test_questionsDisplayed(self, db_session):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        q1 = self.question_dto.new(text="Where is Miami", position=0, game=game)
        self.question_dto.save(q1)
        q2 = self.question_dto.new(text="Where is London", position=1, game=game)
        self.question_dto.save(q2)
        q3 = self.question_dto.new(text="Where is Paris", position=2, game=game)
        self.question_dto.save(q3)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        first_reaction = self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=game.uid,
            )
        )
        attempt_uid = first_reaction.attempt_uid
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=game.uid,
                attempt_uid=attempt_uid,
            )
        )

        another_match = self.match_dto.save(self.match_dto.new())
        self.reaction_dto.save(
            self.reaction_dto.new(
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

    def test_questionDisplayedByGame(self, db_session):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        q1 = self.question_dto.new(text="Where is Miami", position=0, game=game)
        self.question_dto.save(q1)
        q2 = self.question_dto.new(text="Where is London", position=1, game=game)
        self.question_dto.save(q2)
        q3 = self.question_dto.new(text="Where is Paris", position=2, game=game)
        self.question_dto.save(q3)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        first_reaction = self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=game.uid,
            )
        )
        attempt_uid = first_reaction.attempt_uid
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=game.uid,
                attempt_uid=attempt_uid,
            )
        )
        another_match = self.match_dto.save(self.match_dto.new())
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=another_match,
                question=q3,
                user=user,
                game_uid=game.uid,
            )
        )
        status = PlayerStatus(user, match, db_session=db_session)
        status.current_attempt_uid = attempt_uid
        assert status.questions_displayed_by_game(game) == {q2.uid: q2, q1.uid: q1}

    def test_allGamesPlayed_1(self, db_session):
        """
        there is no reaction for q3, that implies was not displayed
        therefore g2 should not be considered
        """
        match = self.match_dto.save(self.match_dto.new())
        g1 = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(g1)
        g2 = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(g2)
        q1 = self.question_dto.new(text="Where is Miami", position=0, game=g1)
        self.question_dto.save(q1)
        q2 = self.question_dto.new(text="Where is London", position=0, game=g2)
        self.question_dto.save(q2)
        q3 = self.question_dto.new(text="Where is Montreal", position=1, game=g2)
        self.question_dto.save(q3)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        first_reaction = self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
            )
        )
        attempt_uid = first_reaction.attempt_uid
        self.reaction_dto.save(
            self.reaction_dto.new(
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

    def test_5(self, db_session):
        """
        GIVEN: a two games match, each game with one question
        WHEN: the user `reacts` to all questions
        THEN: the match should be considered as completed because
                there are 2 reactions with the same attempt_uid
        """
        match = self.match_dto.save(self.match_dto.new())
        g1 = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(g1)
        g2 = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(g2)
        q1 = self.question_dto.new(text="Where is Miami", position=0, game=g1)
        self.question_dto.save(q1)
        q2 = self.question_dto.new(text="Where is London", position=0, game=g2)
        self.question_dto.save(q2)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        status = PlayerStatus(user, match, db_session=db_session)
        first_reaction = self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
            )
        )
        status.current_attempt_uid = first_reaction.attempt_uid
        assert status.questions_displayed() == {q1.uid: q1}
        self.reaction_dto.save(
            self.reaction_dto.new(
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

    def test_6(self, db_session):
        """
        GIVEN: a match with two questions, that can be played 3 times
        WHEN: the user `reacts` to the first question 2 times
        THEN: the match can't be considered completed because, no
                attempt was completed (i.e. there are no 2 reactions
                with the same attempt_uid)
        """
        match = self.match_dto.save(self.match_dto.new(times=3))
        g1 = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(g1)
        q1 = self.question_dto.new(text="Where is Miami", position=0, game=g1)
        self.question_dto.save(q1)
        q2 = self.question_dto.new(text="Where is London", position=1, game=g1)
        self.question_dto.save(q2)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
            )
        )
        another_reaction = self.reaction_dto.save(
            self.reaction_dto.new(
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

    def test_startFreshMatch(self, db_session):
        """
        verify several context related properties
        """
        match = self.match_dto.save(self.match_dto.new())
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        status = PlayerStatus(user, match, db_session=db_session)
        assert status.start_fresh_one()
        assert status.questions_displayed() == {}
        assert status.all_games_played() == {}

    def test_matchTotalScore(self, db_session):
        match = self.match_dto.save(self.match_dto.new())
        g1 = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(g1)
        g2 = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(g2)
        q1 = self.question_dto.new(text="Where is Miami", position=0, game=g1)
        self.question_dto.save(q1)
        q2 = self.question_dto.new(text="Where is London", position=0, game=g2)
        self.question_dto.save(q2)
        q3 = self.question_dto.new(text="Where is Montreal", position=1, game=g2)
        self.question_dto.save(q3)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        first_reaction = self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
                score=3,
            )
        )
        attempt_uid = first_reaction.attempt_uid
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=g2.uid,
                attempt_uid=attempt_uid,
                score=2.4,
            )
        )
        self.reaction_dto.save(
            self.reaction_dto.new(
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


class TestCaseSinglePlayer(TestCaseBase):
    def test_reactionIsCreatedAsSoonAsQuestionIsReturned(self, db_session):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        self.question_dto.save(question)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        question_returned, _ = player.start()

        assert question_returned == question
        assert player.current == question_returned
        assert user.reactions.count() == 1

    def test_reactToFirstQuestion(self, db_session):
        """
        GIVEN: a match with one question only
        WHEN: the user reacts to it
        THEN: the answer is correct because was the only
        one and it was at position 0
        """
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        first_question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        self.question_dto.save(first_question)
        answer = self.answer_dto.new(question=first_question, text="UK", position=0)
        self.answer_dto.save(answer)
        second_question = self.question_dto.new(
            text="Where is Paris?",
            game_uid=game.uid,
            position=1,
        )
        self.question_dto.save(second_question)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        player.start()
        was_correct = player.react(first_question, answer)
        assert user.reactions.count() > 0
        assert player.forward() == second_question
        assert was_correct

    def test_startMatchAlreadyExpired(self, db_session):
        match = self.match_dto.new(to_time=datetime.now() - timedelta(microseconds=10))
        self.match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        self.question_dto.save(question)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        with pytest.raises(MatchError) as e:
            player.start()

        assert e.value.message == "Expired match"

    def test_matchCanBePlayedAnotherTime(self, db_session):
        """
        GIVEN: a match that can be played two times
        WHEN: the user plays once
        THEN: the method `start_fresh_one` should return True
        """
        match = self.match_dto.save(self.match_dto.new(times=2))
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        first_question = self.question_dto.new(
            text="Where is Graz?", game_uid=game.uid, position=0
        )
        self.question_dto.save(first_question)
        first_answer = self.answer_dto.new(
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

    def test_matchCannotBePlayedMoreThanMatchTimes(self, db_session):
        max_times = 2
        match = self.match_dto.save(self.match_dto.new(times=max_times))
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        first_question = self.question_dto.new(
            text="Where is Graz?", game_uid=game.uid, position=0
        )
        self.question_dto.save(first_question)
        first_answer = self.answer_dto.new(
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

    def test_restoreOpenQuestionsMatchFromSecondQuestion(self, db_session):
        match = self.match_dto.save(self.match_dto.new())
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        first_question = self.question_dto.new(
            text="Where is Graz?", game_uid=game.uid, position=0
        )
        self.question_dto.save(first_question)
        second_question = self.question_dto.new(
            text="Where is Istanbul?",
            game_uid=game.uid,
            position=1,
        )
        self.question_dto.save(second_question)

        open_answer_dto = OpenAnswerDTO(session=db_session)
        open_answer_1 = open_answer_dto.new(text="Austria")
        open_answer_dto.save(open_answer_1)

        first_reaction = self.reaction_dto.save(
            self.reaction_dto.new(
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


class TestCaseResumeMatch(TestCaseBase):
    def test_matchCanBeResumedWhenThereIsStillOneQuestionToDisplay(self, db_session):
        match = self.match_dto.save(self.match_dto.new(is_restricted=True))
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        first_question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        self.question_dto.save(first_question)
        answer = self.answer_dto.new(
            question=first_question, text="UK", position=0, is_correct=False
        )
        self.answer_dto.save(answer)
        second_question = self.question_dto.new(
            text="Where is Moscow?",
            game_uid=game.uid,
            position=1,
        )
        self.question_dto.save(second_question)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        player.start()
        was_correct = player.react(first_question, answer)
        assert player.match_can_be_resumed
        assert not was_correct

    def test_matchCanNotBeResumedBecausePublic(self, db_session):
        match = self.match_dto.save(self.match_dto.new(is_restricted=False))
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=db_session)
        player = SinglePlayer(status, user, match, db_session=db_session)
        assert not player.match_can_be_resumed


class TestCasePlayScore(TestCaseBase):
    def test_compute_score(self, db_session):
        match = self.match_dto.save(self.match_dto.new())
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        PlayScore(match.uid, user.uid, 5.5, db_session=db_session).save_to_ranking()

        assert len(RankingDTO(session=db_session).all()) == 1
