import logging
from random import shuffle

from app.domain_service.data_transfer.ranking import RankingDTO
from app.domain_service.data_transfer.reaction import ReactionDTO
from app.exceptions import (
    GameError,
    GameOver,
    MatchError,
    MatchNotPlayableError,
    MatchOver,
)

logger = logging.getLogger(__name__)


class QuestionFactory:
    def __init__(self, game, *displayed_ids):
        self._game = game
        # displayed_ids are ordered based on their display order
        self.displayed_ids = displayed_ids
        self._question = None

    def next(self):
        if not self._game.order:
            questions = self._game.questions
            shuffle(questions)
        else:
            questions = self._game.ordered_questions

        for q in questions:
            if q.uid not in self.displayed_ids:
                self._question = q
                self.displayed_ids += (q.uid,)
                return q

        raise GameOver(f"Game {self._game.uid} has no questions")

    def previous(self):
        # remember that the reaction is not deleted
        questions = (
            self._game.ordered_questions if self._game.order else self._game.questions
        )
        for q in questions:
            if not self._question or len(self.displayed_ids) == 1:
                continue

            if q.uid == self.displayed_ids[-2]:
                self._question = q
                return q

        msg = (
            "No questions were displayed"
            if not self.displayed_ids
            else "Only one question was displayed"
        )
        raise GameError(f"{msg} for Game {self._game.uid}")

    @property
    def current(self):
        return self._question

    @property
    def is_last_question(self):
        questions = (
            self._game.ordered_questions if self._game.order else self._game.questions
        )
        return len(self.displayed_ids) == len(questions)


class GameFactory:
    def __init__(self, match, *played_ids):
        self._match = match
        self.played_ids = played_ids
        self._game = None

    def next(self):
        games = self._match.ordered_games if self._match.order else self._match.games
        for g in games:
            if g.uid not in self.played_ids:
                self.played_ids += (g.uid,)
                self._game = g
                return g

        raise MatchOver(f"Match {self._match.name}")

    def previous(self):
        games = self._match.ordered_games if self._match.order else self._match.games
        for g in games:
            if not self._game or len(self.played_ids) == 1:
                continue

            if g.uid == self.played_ids[-2]:
                self._game = g
                return g

        msg = (
            "No game were played" if not self.played_ids else "Only one game was played"
        )
        raise MatchError(f"{msg} for Match {self._match.name}")

    @property
    def current(self):
        return self._game

    @property
    def match_started(self):
        return len(self.played_ids) > 0

    @property
    def is_last_game(self):
        games = self._match.ordered_games if self._match.order else self._match.games
        return len(self.played_ids) == len(games)


class PlayerStatus:
    def __init__(self, user, match, db_session):
        self._user = user
        self._current_match = match
        self._session = db_session
        self.reaction_dto = ReactionDTO(session=db_session)

    @property
    def _all_reactions_query(self):
        return self.reaction_dto.all_reactions_of_user_to_match(
            self._user, self._current_match
        )  # .filter_by(_answer=None)

    def all_reactions(self):
        return self._all_reactions_query.all()  # TODO to fix: or _open_answer=None

    def questions_displayed(self):
        return {r.question.uid: r.question for r in self._all_reactions_query.all()}

    def questions_displayed_by_game(self, game):
        return {
            r.question.uid: r.question
            for r in self._all_reactions_query.all()
            if r.game.uid == game.uid
        }

    def all_games_played(self):
        return {r.game.uid: r.game for r in self._all_reactions_query.all()}

    def current_score(self):
        return sum(r.score for r in self.all_reactions())

    @property
    def match(self):
        return self._current_match


class SinglePlayer:
    def __init__(self, status, user, match, db_session):
        self._status = status
        self._user = user
        self._match = match
        self._session = db_session
        self.reaction_dto = ReactionDTO(session=db_session)

        self._game_factory = None
        self._question_factory = None
        self._current_reaction = None

    def start(self):
        self._session.refresh(self._match)
        # TODO to fix
        if self._match.left_attempts(self._user) == 0:
            raise MatchNotPlayableError(
                f"User {self._user.email} has no left attempts for Match {self._match.name}"
            )

        if not self._match.is_active:
            raise MatchError("Expired match")

        self._game_factory = GameFactory(self._match, *self._status.all_games_played())
        game = self._game_factory.next()

        self._question_factory = QuestionFactory(
            game, *self._status.questions_displayed()
        )
        question = self._question_factory.next()

        self._current_reaction = self.reaction_dto.new(
            match_uid=self._match.uid,
            user_uid=self._user.uid,
            game_uid=game.uid,
            question_uid=question.uid,
        )
        self.reaction_dto.save(self._current_reaction)

        return question

    @property
    def match_started(self):
        return self._game_factory.match_started

    @property
    def current_game(self):
        return self._game_factory.current

    def next_game(self):
        return self._game_factory.next_game()

    @property
    def can_be_resumed(self):
        return self._game_factory

    @property
    def match_score(self):
        return self._status.total_score()

    def last_reaction(self, question):
        reactions = self.reaction_dto.all_reactions_of_user_to_match(
            self._user, self._match
        ).filter_by(
            _answer=None
        )  # TODO to fix: or _open_answer=None

        if reactions.count() > 0:
            return reactions.first()

        new_reaction = self.reaction_dto.new(
            match_uid=self._match.uid,
            question_uid=question.uid,
            game_uid=question.game.uid,
            user_uid=self._user.uid,
        )
        return self.reaction_dto.save(new_reaction)

    @property
    def match_can_be_resumed(self):
        """Determine if this match can be restored

        By counting the reactions it is possible to
        determine if all questions were displayed
        """
        return (
            self._match.is_restricted
            and len(self._status.all_reactions()) < self._match.questions_count
        )

    def react(self, answer):
        if not self._match.is_active:
            raise MatchError("Expired match")

        if not self._current_reaction:
            self._current_reaction = self.last_reaction(answer.question)
            self._game_factory = GameFactory(
                self._match, *self._status.all_games_played()
            )

            self._question_factory = QuestionFactory(
                self._current_reaction.game, *self._status.questions_displayed()
            )

        self.reaction_dto.record_answer(self._current_reaction, answer)
        return self.forward()

    @property
    def current(self):
        return self._question_factory.current

    def forward(self):
        try:
            return self._question_factory.next()
        except GameOver:
            game = self._game_factory.next()
            self._question_factory = QuestionFactory(
                game, *self._status.questions_displayed()
            )
            return self._question_factory.next()


class PlayScore:
    def __init__(self, match_uid, user_uid, score, db_session):
        self.match_uid = match_uid
        self.user_uid = user_uid
        self.score = score
        self._session = db_session

    def save_to_ranking(self):
        dto = RankingDTO(session=self._session)
        new_ranking = dto.new(
            match_uid=self.match_uid,
            user_uid=self.user_uid,
            score=self.score,
        )
        dto.save(new_ranking)
        return new_ranking
