from datetime import datetime
from math import isclose

import pytest
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.open_answer import OpenAnswerDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.reaction import ReactionDTO, ReactionScore
from app.domain_service.data_transfer.user import UserDTO


class TestCaseReactionModel:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.answer_dto = AnswerDTO(session=db_session)
        self.reaction_dto = ReactionDTO(session=db_session)
        self.match_dto = MatchDTO(session=db_session)
        self.game_dto = GameDTO(session=db_session)
        self.user_dto = UserDTO(session=db_session)

    def t_cannotExistsTwoReactionsOfTheSameUserAtSameTime(self, db_session):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        question = self.question_dto.new(
            text="new-question", position=0, game_uid=game.uid
        )
        self.question_dto.save(question)
        answer = self.answer_dto.new(
            question=question,
            text="question2.answer1",
            position=1,
        )
        self.answer_dto.save(answer)

        now = datetime.now()
        with pytest.raises((IntegrityError, InvalidRequestError)):
            self.reaction_dto.save(
                self.reaction_dto.new(
                    match_uid=match.uid,
                    question_uid=question.uid,
                    answer_uid=answer.uid,
                    user_uid=user.uid,
                    create_timestamp=now,
                    game_uid=game.uid,
                )
            )
            self.reaction_dto.save(
                self.reaction_dto.new(
                    match_uid=match.uid,
                    question_uid=question.uid,
                    answer_uid=answer.uid,
                    user_uid=user.uid,
                    create_timestamp=now,
                    game_uid=game.uid,
                )
            )
        db_session.rollback()

    def t_ifQuestionChangesThenAlsoFKIsUpdatedAndAffectsReaction(self):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        question = self.question_dto.new(text="1+1 is = to", position=0)
        self.question_dto.save(question)
        answer = self.answer_dto.new(question=question, text="2", position=1)
        self.answer_dto.save(answer)
        reaction = self.reaction_dto.new(
            match_uid=match.uid,
            question_uid=question.uid,
            answer_uid=answer.uid,
            user_uid=user.uid,
            game_uid=game.uid,
        )
        self.reaction_dto.save(reaction)
        question.text = "1+2 is = to"
        self.question_dto.save(question)

        assert reaction.question.text == "1+2 is = to"

    def t_whenQuestionIsElapsedAnswerIsNotRecorded(self):
        # and the score remains Null
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        question = self.question_dto.new(text="3*3 = ", time=0, position=0)
        self.question_dto.save(question)
        reaction = self.reaction_dto.new(
            match=match,
            question=question,
            user=user,
            game_uid=game.uid,
        )
        self.reaction_dto.save(reaction)

        answer = self.answer_dto.new(question=question, text="9", position=1)
        self.answer_dto.save(answer)
        self.reaction_dto.record_answer(reaction, answer)

        assert reaction.answer is None
        assert reaction.score is None

    def t_recordAnswerInTime(self):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        question = self.question_dto.new(text="1+1 =", time=2, position=0)
        self.question_dto.save(question)
        reaction = self.reaction_dto.new(
            match=match,
            question=question,
            user=user,
            game_uid=game.uid,
        )
        self.reaction_dto.save(reaction)

        answer = self.answer_dto.new(question=question, text="2", position=1)
        self.answer_dto.save(answer)
        self.reaction_dto.record_answer(reaction, answer)

        assert reaction.answer
        assert reaction.answer_time
        # because the score is computed over the response
        # time and this one variates at each tests run
        # isclose is used to avoid brittleness
        assert isclose(reaction.score, 0.999, rel_tol=0.05)

    def t_reactionTimingIsRecordedAlsoForOpenQuestions(self, db_session):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        question = self.question_dto.new(text="Where is Miami", position=0)
        self.question_dto.save(question)
        reaction = self.reaction_dto.new(
            match=match,
            question=question,
            user=user,
            game_uid=game.uid,
        )
        self.reaction_dto.save(reaction)

        open_answer_dto = OpenAnswerDTO(session=db_session)
        open_answer = open_answer_dto.new(text="Florida")
        open_answer_dto.save(open_answer)

        self.reaction_dto.record_answer(reaction, answer=open_answer)
        assert question.is_open
        assert reaction.answer
        assert reaction.answer_time
        # no score should be computed for open questions
        assert not reaction.score

    def t_allReactionsOfUser(self):
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        q1 = self.question_dto.new(text="t1", position=0)
        self.question_dto.save(q1)
        q2 = self.question_dto.new(text="t2", position=1)
        self.question_dto.save(q2)
        r1 = self.reaction_dto.new(
            match=match, question=q1, user=user, game_uid=game.uid
        )
        self.reaction_dto.save(r1)
        r2 = self.reaction_dto.new(
            match=match, question=q2, user=user, game_uid=game.uid
        )
        self.reaction_dto.save(r2)

        reactions = self.reaction_dto.all_reactions_of_user_to_match(
            user, match, asc=False
        ).all()
        assert len(reactions) == 2
        assert reactions[0] == r2
        assert reactions[1] == r1


class TestCaseReactionScore:
    def t_computeWithOnlyOnTiming(self):
        rs = ReactionScore(timing=0.2, question_time=3, answer_level=None)
        assert rs.value() == 0.933

    def t_computeWithTimingAndLevel(self):
        rs = ReactionScore(timing=0.2, question_time=3, answer_level=2)
        assert isclose(rs.value(), 0.93 * 2, rel_tol=0.05)

    def t_computeScoreForOpenQuestion(self):
        rs = ReactionScore(timing=0.2, question_time=None, answer_level=None)
        assert rs.value() == 0
