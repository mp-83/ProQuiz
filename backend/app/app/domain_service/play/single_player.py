import logging
from random import shuffle

from app.domain_service.data_transfer.ranking import RankingDTO
from app.domain_service.data_transfer.reaction import ReactionDTO
from app.exceptions import (
    GameError,
    GameOver,
    HuntOver,
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
        questions = self._game.questions.filter_by(uid__notin=self.displayed_ids).all()
        if not self._game.order:
            shuffle(questions)

        if questions:
            self._question = questions[0]
            self.displayed_ids += (questions[0].uid,)
            return questions[0]

        raise GameOver(f"Game {self._game.uid} has no questions")

    def previous(self):
        # remember that the reaction is not deleted
        if len(self.displayed_ids) > 1:
            return self._game.questions.filter_by(
                uid=self.displayed_ids[-2]
            ).one_or_none()

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
        return len(self.displayed_ids) == self._game.questions.count()


class GameFactory:
    def __init__(self, match, *played_ids):
        self._match = match
        self.played_ids = played_ids
        self._game = None

    def next(self):
        games = self._match.games.filter_by(uid__notin=self.played_ids).all()
        if not self._match.order:
            shuffle(games)

        if games:
            self.played_ids += (games[0].uid,)
            self._game = games[0]
            return games[0]

        raise MatchOver(f"Match {self._match.name}")

    def previous(self):
        games = self._match.games if self._match.order else self._match.games
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
        return len(self.played_ids) == self._match.games.count()


class PlayerStatus:
    def __init__(self, user, match, db_session):
        self._user = user
        self._current_match = match
        self._session = db_session
        self.reaction_dto = ReactionDTO(session=db_session)
        self.__current_attempt_uid = None

    @property
    def current_attempt_uid(self):
        return self.__current_attempt_uid

    @current_attempt_uid.setter
    def current_attempt_uid(self, value):
        self.__current_attempt_uid = value

    @property
    def _all_reactions_query(self):
        return self._user.reactions.filter_by(
            match_uid=self._current_match.uid, attempt_uid=self.__current_attempt_uid
        )

    def all_reactions(self):
        return self._all_reactions_query.all()

    def questions_displayed(self):
        return {r.question.uid: r.question for r in self._all_reactions_query.all()}

    def questions_displayed_by_game(self, game):
        return {
            r.question.uid: r.question
            for r in self._all_reactions_query.filter_by(game_uid=game.uid).all()
        }

    def match_completed(self):
        return (
            self._current_match.reactions.filter_by(
                attempt_uid=self.__current_attempt_uid
            ).count()
            - len(self._current_match.questions_list)
            == 0
        )

    def _no_attempts(self):
        # tODO to fix and/or remove it as it always false,
        # since a Reaction is created immediately after /start
        return self.match.reactions.filter_by(user_uid=self._user.uid).count() == 0

    def start_fresh_one(self):
        return self._no_attempts() or self._current_match.left_attempts(self._user) > 0

    def all_games_played(self):
        """
        Return games that were completed
        """
        return {
            game.uid: game
            for game in self._current_match.games
            if (
                game.questions.count() > 0
                and game.questions.count()
                == self._all_reactions_query.filter_by(game_uid=game.uid).count()
            )
        }

    def current_score(self):
        """Sum the scores of all reactions for the match

        If reaction.score is None it either means the
        the answer was recorded after question.time or
        it was an open-answer
        """
        return sum(r.score or 0 for r in self.all_reactions())

    @property
    def match(self):
        return self._current_match


class SinglePlayer:
    def __init__(self, status: "PlayerStatus", user, match, db_session):
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

        return question, self._current_reaction.attempt_uid

    @property
    def match_started(self):
        return self._game_factory.match_started

    @property
    def current_game(self):
        return self._game_factory.current

    def next_game(self):
        return self._game_factory.next_game()

    def _new_reaction(self, question, attempt_uid):
        new_reaction = self.reaction_dto.new(
            match_uid=self._match.uid,
            question_uid=question.uid,
            game_uid=question.game.uid,
            user_uid=self._user.uid,
            attempt_uid=attempt_uid,
        )
        return self.reaction_dto.save(new_reaction)

    def last_reaction(self, question):
        match_reactions = self._user.reactions.filter_by(match_uid=self._match.uid)
        attempt_uid = (
            match_reactions.first().attempt_uid if match_reactions.count() > 0 else None
        )

        question_reaction = match_reactions.filter_by(
            question_uid=question.uid, update_timestamp=None
        ).one_or_none()
        if question_reaction:
            return question_reaction

        return self._new_reaction(question, attempt_uid)

    def react(self, question, answer=None, open_answer=None):
        if not self._current_reaction:
            self._current_reaction = self.last_reaction(question)
            self._game_factory = GameFactory(
                self._match, *self._status.all_games_played()
            )

            self._question_factory = QuestionFactory(
                self._current_reaction.game, *self._status.questions_displayed()
            )
        elif self._current_reaction.question != question:
            attempt_uid = self._current_reaction.attempt_uid
            self._current_reaction = self._new_reaction(question, attempt_uid)

        was_correct = self.reaction_dto.record_answer(
            self._current_reaction, answer=answer, open_answer=open_answer
        )
        self.end_now(was_correct)
        return was_correct

    @property
    def current(self):
        return self._question_factory.current

    def end_now(self, was_correct):
        if not self._match.treasure_hunt or was_correct:
            return

        raise HuntOver("Hunt-treasure match over")

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
