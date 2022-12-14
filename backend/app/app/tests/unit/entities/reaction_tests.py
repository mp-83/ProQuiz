from datetime import datetime, timedelta
from math import isclose

import pytest
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from app.domain_service.data_transfer.reaction import ReactionScore


class TestCaseReactionModel:
    def test_1(
        self,
        db_session,
        match_dto,
        game_dto,
        question_dto,
        answer_dto,
        reaction_dto,
        user_dto,
    ):
        """
        GIVEN: a question of a match
        WHEN: a reaction of the user is created
        THEN: another reaction for the same
                user and question cannot be created
                at the same time
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        question = question_dto.new(text="new-question", position=0, game_uid=game.uid)
        question_dto.save(question)
        answer = answer_dto.new(
            question=question,
            text="question2.answer1",
            position=1,
        )
        answer_dto.save(answer)

        now = datetime.now()
        with pytest.raises((IntegrityError, InvalidRequestError)):
            reaction_dto.save(
                reaction_dto.new(
                    match_uid=match.uid,
                    question_uid=question.uid,
                    answer_uid=answer.uid,
                    user_uid=user.uid,
                    create_timestamp=now,
                    game_uid=game.uid,
                )
            )
            reaction_dto.save(
                reaction_dto.new(
                    match_uid=match.uid,
                    question_uid=question.uid,
                    answer_uid=answer.uid,
                    user_uid=user.uid,
                    create_timestamp=now,
                    game_uid=game.uid,
                )
            )
        db_session.rollback()

    def test_2(
        self, match_dto, game_dto, question_dto, answer_dto, reaction_dto, user_dto
    ):
        """
        GIVEN: an existing reaction of a user to a question
        WHEN: when question's text is updated
        THEN: the reaction should reflect the change
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        question = question_dto.new(text="1+1 is = to", position=0)
        question_dto.save(question)
        answer = answer_dto.new(question=question, text="2", position=1)
        answer_dto.save(answer)
        reaction = reaction_dto.new(
            match_uid=match.uid,
            question_uid=question.uid,
            answer_uid=answer.uid,
            user_uid=user.uid,
            game_uid=game.uid,
        )
        reaction_dto.save(reaction)
        question.text = "1+2 is = to"
        question_dto.save(question)

        assert reaction.question.text == "1+2 is = to"

    def test_3(
        self,
        match_dto,
        game_dto,
        question_dto,
        answer_dto,
        reaction_dto,
        user_dto,
        mocker,
    ):
        """
        GIVEN: an existing reaction of a user created
                when the question is displayed
        WHEN: the question's time is elapsed and the
                user answers
        THEN: the answer should not be recorded, therefore
        is not correct
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        question = question_dto.new(text="3*3 = ", time=5, position=0)
        question_dto.save(question)
        reaction = reaction_dto.new(
            match=match,
            question=question,
            user=user,
            game_uid=game.uid,
        )
        reaction_dto.save(reaction)

        datetime_mock = mocker.patch(
            "app.domain_service.data_transfer.reaction.datetime"
        )
        datetime_mock.now.return_value = datetime.now() + timedelta(seconds=7)
        answer = answer_dto.new(
            question=question, text="9", position=1, is_correct=True
        )
        answer_dto.save(answer)
        was_correct = reaction_dto.record_answer(reaction, answer)

        assert reaction.answer is None
        assert reaction.score is None
        assert not was_correct

    def test_4(
        self, match_dto, game_dto, question_dto, answer_dto, reaction_dto, user_dto
    ):
        """
        GIVEN: an existing reaction of a user created
                when the question is displayed
        WHEN: the user's answers before the question's
                time is elapsed
        THEN: the answer is recorded
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        question = question_dto.new(text="1+1 =", time=2, position=0)
        question_dto.save(question)
        reaction = reaction_dto.new(
            match=match,
            question=question,
            user=user,
            game_uid=game.uid,
        )
        reaction_dto.save(reaction)

        answer = answer_dto.new(question=question, text="2", position=1)
        answer_dto.save(answer)
        was_correct = reaction_dto.record_answer(reaction, answer)

        assert reaction.answer
        assert reaction.answer_time
        assert not was_correct
        # because the score is computed over the response
        # time and this one variates at each tests run
        # isclose is used to avoid brittleness
        assert isclose(reaction.score, 0.999, rel_tol=0.05)

    def test_5(
        self, match_dto, game_dto, question_dto, open_answer_dto, reaction_dto, user_dto
    ):
        """
        GIVEN: an existing reaction of a user created
                when the question is displayed
        WHEN: the user's replies with an OpenAnswer
        THEN: it should be associated with the reaction and no score
                should be computed because it is an OpenAnswer
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        question = question_dto.new(text="Where is Miami", position=0)
        question_dto.save(question)
        reaction = reaction_dto.new(
            match=match,
            question=question,
            user=user,
            game_uid=game.uid,
        )
        reaction_dto.save(reaction)

        open_answer = open_answer_dto.new(text="Miami is in Florida")
        open_answer_dto.save(open_answer)

        was_correct = reaction_dto.record_answer(reaction, open_answer=open_answer)
        assert question.is_open
        assert reaction.answer == open_answer
        assert reaction.answer_time
        assert not reaction.score
        assert not was_correct

    def test_6(self, match_dto, game_dto, question_dto, reaction_dto, user_dto):
        """
        GIVEN: two existing reactions of a user for two
                distinct matches
        WHEN: the reverse relationship is queried for the
                user's reactions to the first match
        THEN: only two reactions should be returned
                from the reactions property and their
                attempt_uid should be different
        """
        match_1 = match_dto.save(match_dto.new())
        game_1 = game_dto.new(match_uid=match_1.uid)
        game_dto.save(game_1)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        q1 = question_dto.new(text="Where is Choir?", position=0)
        question_dto.save(q1)
        r1 = reaction_dto.new(
            match=match_1, question=q1, user=user, game_uid=game_1.uid
        )
        reaction_dto.save(r1)

        match_2 = match_dto.save(match_dto.new())
        game_2 = game_dto.new(match_uid=match_2.uid, index=0)
        game_dto.save(game_2)
        q2 = question_dto.new(text="Where is Basel?", game_uid=game_2.uid, position=0)
        question_dto.save(q2)

        r2 = reaction_dto.new(
            match=match_2, question=q2, user=user, game_uid=game_2.uid
        )
        reaction_dto.save(r2)

        reactions = user.reactions.filter_by(match_uid=match_1.uid).all()
        assert len(reactions) == 1
        assert reactions[0] == r1
        assert match_1.reactions.count() == 1
        assert match_1.reactions.first() == r1
        assert user.reactions[0].attempt_uid != user.reactions[1].attempt_uid

    def test_7(
        self, match_dto, game_dto, question_dto, open_answer_dto, reaction_dto, user_dto
    ):
        """
        GIVEN: three reactions to a match, each from different user
        WHEN: the open_answer property is accessed
        THEN: it returns a list of two OpenAnswer objects for this
                match, because one reaction didn't `contain` an answer.
                All reactions, because they belong to different users
                are different
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        user_1 = user_dto.new(email="user_1@test.project")
        user_dto.save(user_1)
        question_1 = question_dto.new(text="Where is Lausanne?", position=0)
        question_dto.save(question_1)

        open_answer_1 = open_answer_dto.new(text="Lausanne is in Switzerland.")
        open_answer_dto.save(open_answer_1)
        r1 = reaction_dto.new(
            match=match,
            question=question_1,
            user=user_1,
            game_uid=game.uid,
            open_answer_uid=open_answer_1.uid,
        )
        reaction_dto.save(r1)

        user_2 = user_dto.new(email="user_2@test.project")
        user_dto.save(user_2)
        open_answer_2 = open_answer_dto.new(text="Lausanne is in France.")
        open_answer_dto.save(open_answer_2)
        r2 = reaction_dto.new(
            match=match,
            question=question_1,
            user=user_2,
            game_uid=game.uid,
            open_answer_uid=open_answer_2.uid,
        )
        reaction_dto.save(r2)

        user_3 = user_dto.new(email="user_3@test.project")
        user_dto.save(user_3)
        r3 = reaction_dto.new(
            match=match, question=question_1, user=user_2, game_uid=game.uid
        )
        reaction_dto.save(r3)

        assert match.open_answers == [open_answer_1, open_answer_2]
        assert r2.attempt_uid != r3.attempt_uid


class TestCaseReactionScore:
    def test_1(self):
        """
        GIVEN: a ReactionScore where only the question's time
                is specified
        WHEN: the value is computed
        THEN: result should be the expected
        """
        rs = ReactionScore(timing=0.2, question_time=3, answer_level=None)
        assert rs.value() == 0.933

    def test_2(self):
        """
        GIVEN: a ReactionScore where the question's time and
                the answer's level are specified
        WHEN: the value is computed
        THEN: result should be the expected
        """
        rs = ReactionScore(timing=0.2, question_time=3, answer_level=2)
        assert isclose(rs.value(), 0.93 * 2, rel_tol=0.05)

    def test_3(self):
        """
        GIVEN: a ReactionScore associated to an open question
        WHEN: the value is computed
        THEN: result should be zero
        """
        rs = ReactionScore(timing=0.2, question_time=None, answer_level=None)
        assert rs.value() == 0
