from datetime import datetime, timedelta

import pytest

from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
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


class TestCaseBase:
    @pytest.fixture(autouse=True)
    def setUp(self, dbsession):
        self.question_dto = QuestionDTO(session=dbsession)
        self.match_dto = MatchDTO(session=dbsession)
        self.reaction_dto = ReactionDTO(session=dbsession)
        self.answer_dto = AnswerDTO(session=dbsession)
        self.game_dto = GameDTO(session=dbsession)
        self.user_dto = UserDTO(session=dbsession)


class TestCaseQuestionFactory(TestCaseBase):
    def t_nextQuestionWhenNotOrdered(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1, order=False)
        self.game_dto.save(game)
        q_berlin = self.question_dto.new(
            text="Where is Berlin?", game_uid=game.uid, position=0, db_session=dbsession
        )
        self.question_dto.save(q_berlin)
        q_zurich = self.question_dto.new(
            text="Where is Zurich?", game_uid=game.uid, position=1, db_session=dbsession
        )
        self.question_dto.save(q_zurich)

        question_factory = QuestionFactory(game, *())
        assert question_factory.next() == q_berlin
        assert question_factory.next() == q_zurich
        assert question_factory.current == q_zurich

    def t_nextQuestionWhenOrdered(self, dbsession):
        """Questions are inversely created
        to make the ordering meaningful.
        """
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        second = self.question_dto.new(
            text="Where is London?", game_uid=game.uid, position=1, db_session=dbsession
        )
        self.question_dto.save(second)
        first = self.question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=0, db_session=dbsession
        )
        self.question_dto.save(first)

        question_factory = QuestionFactory(game, *())
        assert question_factory.next() == first
        assert question_factory.next() == second

    def t_gameOverWhenThereAreNoQuestions(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)

        question_factory = QuestionFactory(game, *())
        with pytest.raises(GameOver):
            question_factory.next()

    def t_gameIsOverAfterLastQuestion(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=0, db_session=dbsession
        )
        self.question_dto.save(question)

        question_factory = QuestionFactory(game, *())
        question_factory.next()
        with pytest.raises(GameOver):
            question_factory.next()

    def t_isLastQuestion(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is Amsterdam?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        question = self.question_dto.new(
            text="Where is Lion?", game_uid=game.uid, position=1, db_session=dbsession
        )
        self.question_dto.save(question)

        question_factory = QuestionFactory(game)
        question_factory.next()
        assert not question_factory.is_last_question
        question_factory.next()
        assert question_factory.is_last_question

    def t_previousQuestion(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        first = self.question_dto.new(
            text="Where is Amsterdam?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(first)
        second = self.question_dto.new(
            text="Where is Lion?", game_uid=game.uid, position=1, db_session=dbsession
        )
        self.question_dto.save(second)

        question_factory = QuestionFactory(game)
        question_factory.next()
        question_factory.next()
        assert question_factory.previous() == first

    def t_callingPreviousWithoutNext(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is Amsterdam?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        question = self.question_dto.new(
            text="Where is Lion?", game_uid=game.uid, position=1, db_session=dbsession
        )
        self.question_dto.save(question)

        question_factory = QuestionFactory(game)
        with pytest.raises(GameError):
            question_factory.previous()

    def t_callingPreviousRightAfterFirstNext(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is Amsterdam?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        question = self.question_dto.new(
            text="Where is Lion?", game_uid=game.uid, position=1, db_session=dbsession
        )
        self.question_dto.save(question)

        question_factory = QuestionFactory(game)
        question_factory.next()
        with pytest.raises(GameError):
            question_factory.previous()


class TestCaseGameFactory(TestCaseBase):
    def t_nextGameWhenOrdered(self, dbsession):
        match = self.match_dto.save(self.match_dto.new(order=True))
        second = self.game_dto.new(match_uid=match.uid, index=2)
        self.game_dto.save(second)
        first = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(first)

        game_factory = GameFactory(match, *())
        assert game_factory.next() == first
        assert game_factory.next() == second

    def t_matchWithoutGamesThrowsError(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game_factory = GameFactory(match, *())

        with pytest.raises(MatchOver):
            game_factory.next()

        dbsession.rollback()

    def t_matchStarted(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        game_factory = GameFactory(match, *())

        assert not game_factory.match_started

    def t_isLastGame(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        game_factory = GameFactory(match, *())

        game_factory.next()
        assert not game_factory.is_last_game
        game_factory.next()
        assert game_factory.is_last_game

    def t_nextOverTwoSessions(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        g1 = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(g1)
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        game_factory = GameFactory(match, g1.uid)

        game_factory.next()
        assert game_factory.is_last_game

    def t_callingPreviousRightAfterFirstNext(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        game_factory = GameFactory(match, *())

        game_factory.next()
        with pytest.raises(MatchError):
            game_factory.previous()

    def t_callingPreviousWithoutNext(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        game_factory = GameFactory(match, *())

        with pytest.raises(MatchError):
            game_factory.previous()


class TestCaseStatus(TestCaseBase):
    def t_questionsDisplayed(self, dbsession, emitted_queries):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        q1 = self.question_dto.new(
            text="Where is Miami", position=0, game=game, db_session=dbsession
        )
        self.question_dto.save(q1)
        q2 = self.question_dto.new(
            text="Where is London", position=1, game=game, db_session=dbsession
        )
        self.question_dto.save(q2)
        q3 = self.question_dto.new(
            text="Where is Paris", position=2, game=game, db_session=dbsession
        )
        self.question_dto.save(q3)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=game.uid,
                db_session=dbsession,
            )
        )

        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=game.uid,
                db_session=dbsession,
            )
        )

        another_match = self.match_dto.save(self.match_dto.new())
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=another_match,
                question=q3,
                user=user,
                game_uid=game.uid,
                db_session=dbsession,
            )
        )
        status = PlayerStatus(user, match, db_session=dbsession)
        before = len(emitted_queries)
        assert status.questions_displayed() == {q2.uid: q2, q1.uid: q1}
        assert len(emitted_queries) == before + 1

    def t_questionDisplayedByGame(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        q1 = self.question_dto.new(
            text="Where is Miami", position=0, game=game, db_session=dbsession
        )
        self.question_dto.save(q1)
        q2 = self.question_dto.new(
            text="Where is London", position=1, game=game, db_session=dbsession
        )
        self.question_dto.save(q2)
        q3 = self.question_dto.new(
            text="Where is Paris", position=2, game=game, db_session=dbsession
        )
        self.question_dto.save(q3)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=game.uid,
                db_session=dbsession,
            )
        )

        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=game.uid,
                db_session=dbsession,
            )
        )
        another_match = self.match_dto.save(self.match_dto.new())
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=another_match,
                question=q3,
                user=user,
                game_uid=game.uid,
                db_session=dbsession,
            )
        )
        status = PlayerStatus(user, match, db_session=dbsession)
        assert status.questions_displayed_by_game(game) == {q2.uid: q2, q1.uid: q1}

    def t_allGamesPlayed(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        g1 = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(g1)
        g2 = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(g2)
        q1 = self.question_dto.new(
            text="Where is Miami", position=0, game=g1, db_session=dbsession
        )
        self.question_dto.save(q1)
        q2 = self.question_dto.new(
            text="Where is London", position=0, game=g2, db_session=dbsession
        )
        self.question_dto.save(q2)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
                db_session=dbsession,
            )
        )
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=g2.uid,
                db_session=dbsession,
            )
        )

        status = PlayerStatus(user, match, db_session=dbsession)
        assert status.all_games_played() == {g1.uid: g1, g2.uid: g2}

    def t_matchTotalScore(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        g1 = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(g1)
        g2 = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(g2)
        q1 = self.question_dto.new(
            text="Where is Miami", position=0, game=g1, db_session=dbsession
        )
        self.question_dto.save(q1)
        q2 = self.question_dto.new(
            text="Where is London", position=0, game=g2, db_session=dbsession
        )
        self.question_dto.save(q2)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q1,
                user=user,
                game_uid=g1.uid,
                score=3,
                db_session=dbsession,
            )
        )
        self.reaction_dto.save(
            self.reaction_dto.new(
                match=match,
                question=q2,
                user=user,
                game_uid=g2.uid,
                score=2.4,
                db_session=dbsession,
            )
        )
        status = PlayerStatus(user, match, db_session=dbsession)
        assert status.current_score() == 5.4


class TestCaseSinglePlayer(TestCaseBase):
    def t_reactionIsCreatedAsSoonAsQuestionIsReturned(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        question_displayed = player.start()

        assert question_displayed == question
        assert player.current == question_displayed
        assert self.reaction_dto.count() == 1

    def t_reactToFirstQuestion(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        first = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(first)
        answer = self.answer_dto.new(question=first, text="UK", position=1)
        self.answer_dto.save(answer)
        second = self.question_dto.new(
            text="Where is Paris?",
            game_uid=game.uid,
            position=1,
        )
        self.question_dto.save(second)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        player.start()
        next_q = player.react(answer)

        assert len(user.reactions)
        assert next_q == second

    def t_matchAtStartTime(self, dbsession):
        match = self.match_dto.new(to_time=datetime.now() - timedelta(microseconds=10))
        self.match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        with pytest.raises(MatchError) as e:
            player.start()

        assert e.value.message == "Expired match"

    def t_matchRightBeforeReaction(self, dbsession):
        # the to_time attribute is set right before the player initialisation
        # to bypass the is_active check inside start() and fail at reaction
        # time (where is expected)
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        answer = self.answer_dto.new(question=question, text="UK", position=1)
        self.answer_dto.save(answer)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        match.to_time = datetime.now() + timedelta(microseconds=8000)
        self.match_dto.save(match)
        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        player.start()
        with pytest.raises(MatchError) as e:
            player.react(answer)

        assert e.value.message == "Expired match"

    def t_matchCannotBePlayedMoreThanMatchTimes(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?", game_uid=game.uid, position=0, db_session=dbsession
        )
        self.question_dto.save(question)

        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        assert player.start() == question

        with pytest.raises(MatchNotPlayableError):
            player.start()

        assert match.reactions
        dbsession.rollback()

    def t_matchOver(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=2,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        answer = self.answer_dto.new(question=question, text="UK", position=1, level=2)
        self.answer_dto.save(answer)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        player.start()
        with pytest.raises(MatchOver):
            player.react(answer)

    def t_playMatchOverMultipleRequests(self, dbsession):
        # the SinglePlayer is instanced multiple times
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=1, order=False)
        self.game_dto.save(game)
        first = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(first)
        first_answer = self.answer_dto.new(question=first, text="UK", position=1)
        self.answer_dto.save(first_answer)
        second = self.question_dto.new(
            text="Where is Paris?",
            game_uid=game.uid,
            position=1,
            db_session=dbsession,
        )
        self.question_dto.save(second)
        second_answer = self.answer_dto.new(question=second, text="France", position=1)
        self.answer_dto.save(second_answer)
        third = self.question_dto.new(
            text="Where is Dublin?",
            game_uid=game.uid,
            position=2,
            db_session=dbsession,
        )
        self.question_dto.save(third)
        third_answer = self.answer_dto.new(question=third, text="Ireland", position=1)
        self.answer_dto.save(third_answer)

        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        assert player.start() == first
        next_q = player.react(first_answer)
        assert next_q == second

        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        next_q = player.react(second_answer)

        assert user.reactions[1].question == second
        assert next_q == third
        player = SinglePlayer(status, user, match, db_session=dbsession)
        with pytest.raises(MatchOver):
            player.react(third_answer)


class TestCaseResumeMatch(TestCaseBase):
    def t_matchCanBeResumedWhenThereIsStillOneQuestionToDisplay(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            db_session=dbsession,
        ).save()
        answer = self.answer_dto.new(question=question, text="UK", position=1)
        self.answer_dto.save(answer)
        question = self.question_dto.new(
            text="Where is Moscow?",
            game_uid=game.uid,
            position=1,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        player.start()
        player.react(answer)
        assert player.match_can_be_resumed

    def t_matchCanNotBeResumedBecausePublic(self, dbsession):
        match = self.match_dto.save(self.match_dto.new(is_restricted=False))
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        status = PlayerStatus(user, match, db_session=dbsession)
        player = SinglePlayer(status, user, match, db_session=dbsession)
        assert not player.match_can_be_resumed


class TestCasePlayScore(TestCaseBase):
    def t_compute_score(self, dbsession):
        match = self.match_dto.save(self.match_dto.new())
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        PlayScore(match.uid, user.uid, 5.5, db_session=dbsession).save_to_ranking()

        assert len(RankingDTO(session=dbsession).all()) == 1
