from datetime import datetime, timedelta
from math import isclose

import pytest
from app.db.utils import StoreConfig
from app.constants import MATCH_HASH_LEN, MATCH_PASSWORD_LEN
from app.entities import (
    Answer,
    Answers,
    Game,
    Match,
    OpenAnswer,
    Question,
    Questions,
    Reaction,
    Reactions,
    User,
)
from app.entities.match import MatchCode, MatchHash, MatchPassword
from app.entities.reaction import ReactionScore
from app.entities.user import UserFactory
from app.exceptions import NotUsableQuestionError
from sqlalchemy.exc import IntegrityError, InvalidRequestError


class TestCaseUserFactory:
    def t_fetchNewSignedUser(self, dbsession, monkeypatch):
        monkeypatch.setenv(
            "SIGNED_KEY", "3ba57f9a004e42918eee6f73326aa89d", prepend=None
        )
        signed_user = UserFactory(original_email="test@progame.io").fetch()
        assert signed_user.email == "916a55cf753a5c847b861df2bdbbd8de@progame.io"
        assert signed_user.email_digest == "916a55cf753a5c847b861df2bdbbd8de"

    def t_fetchExistingSignedUser(self, dbsession, monkeypatch):
        monkeypatch.setenv(
            "SIGNED_KEY", "3ba57f9a004e42918eee6f73326aa89d", prepend=None
        )
        signed_user = User(
            email_digest="916a55cf753a5c847b861df2bdbbd8de",
            token_digest="2357e975e4daaee0348474750b792660",
        ).save()
        assert signed_user is not None
        assert (
            UserFactory(original_email="test@progame.io", token="25111961").fetch()
            == signed_user
        )

    def t_fetchUnsignedUserShouldReturnNewUserEveryTime(self, dbsession, mocker):
        # called twice to showcase the expected behaviour
        mocker.patch(
            "codechallenge.entities.user.uuid4",
            return_value=mocker.Mock(hex="3ba57f9a004e42918eee6f73326aa89d"),
        )
        unsigned_user = UserFactory().fetch()
        assert unsigned_user.email == "uns-3ba57f9a004e42918eee6f73326aa89d@progame.io"
        assert not unsigned_user.token_digest
        mocker.patch(
            "codechallenge.entities.user.uuid4",
            return_value=mocker.Mock(hex="eee84145094cc69e4f816fd9f435e6b3"),
        )
        unsigned_user = UserFactory().fetch()
        assert unsigned_user.email == "uns-eee84145094cc69e4f816fd9f435e6b3@progame.io"
        assert not unsigned_user.token_digest

    def t_fetchSignedUserWithoutOriginalEmailCreatesNewUser(
        self, dbsession, monkeypatch
    ):
        monkeypatch.setenv(
            "SIGNED_KEY", "3ba57f9a004e42918eee6f73326aa89d", prepend=None
        )
        signed_user = UserFactory(signed=True).fetch()
        assert signed_user.email == "9a1cfb41abc50c3f37630b673323cef5@progame.io"
        assert signed_user.email_digest == "9a1cfb41abc50c3f37630b673323cef5"

    def t_createNewInternalUser(self, dbsession):
        internal_user = UserFactory(
            email="user@test.project", password="password"
        ).fetch()
        assert internal_user.email == "user@test.project"
        assert internal_user.check_password("password")
        assert internal_user.create_timestamp is not None

    def t_fetchExistingInternalUser(self, dbsession):
        new_internal_user = UserFactory(
            email="internal@progame.io", password="password"
        ).fetch()
        existing_user = UserFactory(email=new_internal_user.email).fetch()
        assert existing_user == new_internal_user


class TestCaseQuestion:
    def t_theQuestionAtPosition(self, fillTestingDB):
        question = Question().at_position(0)
        assert question.text == "q1.text"
        assert question.create_timestamp is not None

    def t_newCreatedAnswersShouldBeAvailableFromTheQuestion(self, fillTestingDB):
        question = Question().at_position(0)
        Answer(question=question, text="question2.answer1", position=1).save()
        Answer(question=question, text="question2.answer2", position=2).save()
        assert Answers.count() == 2
        assert question.answers[0].question_uid == question.uid

    def t_editingTextOfExistingQuestion(self, fillTestingDB):
        question = Question().at_position(1)
        question.update(text="new-text")
        assert question.text == "new-text"

    def t_createQuestionWithoutPosition(self, fillTestingDB):
        new_question = Question(text="new-question", position=1).save()
        assert new_question.is_open
        assert new_question.is_template

    def t_allAnswersOfAQuestionMustDiffer(self, fillTestingDB):
        question = Question().at_position(1)
        with pytest.raises((IntegrityError, InvalidRequestError)):
            question.answers.extend(
                [
                    Answer(text="question2.answer1", position=1),
                    Answer(text="question2.answer1", position=2),
                ]
            )
            question.save()

        current_session = StoreConfig().session
        current_session.rollback()

    def t_createManyQuestionsAtOnce(self, dbsession):
        data = {
            "text": "Following the machine’s debut, Kempelen was reluctant to display the Turk because",
            "answers": [
                {"text": "The machine was undergoing repair"},
                {
                    "text": "He had dismantled it following its match with Sir Robert Murray Keith."
                },
                {"text": "He preferred to spend time on his other projects."},
                {"text": "It had been destroyed by fire."},
            ],
            "position": 0,
        }
        new_question = Question(text=data["text"], position=data["position"])
        new_question.create_with_answers(data["answers"])

        expected = {e["text"] for e in data["answers"]}
        assert new_question
        assert {e.text for e in new_question.answers} == expected
        assert Answer.with_text("The machine was undergoing repair").is_correct

    def t_cloningQuestion(self, dbsession):
        new_question = Question(text="new-question", position=0).save()
        Answer(
            question_uid=new_question.uid,
            text="The machine was undergoing repair",
            position=0,
        ).save()
        cloned = new_question.clone()
        assert new_question.uid != cloned.uid
        assert new_question.answers[0] != cloned.answers[0]

    def t_questionsAnswersAreOrderedByDefault(self, dbsession):
        # the reverse relation fields .answers is ordered by default
        question = Question(text="new-question", position=0).save()
        Answer(question_uid=question.uid, text="Answer1", position=0).save()
        Answer(question_uid=question.uid, text="Answer2", position=1).save()

        assert question.answers[0].text == "Answer1"
        assert question.answers[1].text == "Answer2"

    def t_updateAnswers(self, dbsession):
        question = Question(text="new-question", position=0).save()
        a1 = Answer(question_uid=question.uid, text="Answer1", position=0).save()
        a2 = Answer(question_uid=question.uid, text="Answer2", position=1).save()
        a3 = Answer(question_uid=question.uid, text="Answer3", position=2).save()

        ans_2_json = a2.json
        ans_2_json.update(text="Answer text 2")
        question.update_answers([a3.json, a1.json, ans_2_json])
        assert question.answers_by_position[0].text == "Answer3"
        assert question.answers_by_position[1].text == "Answer1"
        assert question.answers_by_position[2].text == "Answer text 2"


class TestCaseMatchModel:
    def t_questionsPropertyReturnsTheExpectedResults(self, dbsession):
        match = Match().save()
        first_game = Game(match_uid=match.uid, index=0).save()
        Question(text="Where is London?", game_uid=first_game.uid, position=0).save()
        second_game = Game(match_uid=match.uid, index=1).save()
        Question(text="Where is Vienna?", game_uid=second_game.uid, position=0).save()
        assert match.questions[0][0].text == "Where is London?"
        assert match.questions[0][0].game == first_game
        assert match.questions[1][0].text == "Where is Vienna?"
        assert match.questions[1][0].game == second_game

    def t_createMatchWithHash(self, dbsession):
        match = Match(with_code=False).save()
        assert match.uhash is not None
        assert len(match.uhash) == MATCH_HASH_LEN

    def t_createRestrictedMatch(self, dbsession):
        match = Match(is_restricted=True).save()
        assert match.uhash
        assert len(match.password) == MATCH_PASSWORD_LEN

    def t_updateTextExistingQuestion(self, dbsession):
        match = Match().save()
        first_game = Game(match_uid=match.uid, index=1).save()
        question = Question(
            text="Where is London?", game_uid=first_game.uid, position=0
        ).save()

        n = Questions.count()
        match.update_questions(
            [
                {
                    "uid": question.uid,
                    "text": "What is the capital of Norway?",
                }
            ],
        )
        no_new_questions = n == Questions.count()
        assert no_new_questions
        assert question.text == "What is the capital of Norway?"

    def t_createMatchUsingTemplateQuestions(self, dbsession):
        question_ids = [
            Question(text="Where is London?", position=0).save().uid,
            Question(text="Where is Vienna?", position=1).save().uid,
        ]
        Answer(
            question_uid=question_ids[0], text="question2.answer1", position=1
        ).save()

        new_match = Match().save()
        questions_cnt = Questions.count()
        answers_cnt = Answers.count()
        new_match.import_template_questions(*question_ids)
        assert Questions.count() == questions_cnt + 2
        assert Answers.count() == answers_cnt + 0

    def t_cannotUseIdsOfQuestionAlreadyAssociateToAGame(self, dbsession):
        match = Match().save()
        first_game = Game(match_uid=match.uid, index=2).save()
        question = Question(
            text="Where is London?", game_uid=first_game.uid, position=3
        ).save()
        question_ids = [question.uid]
        with pytest.raises(NotUsableQuestionError):
            match.import_template_questions(*question_ids)

    def t_matchCannotBePlayedIfAreNoLeftAttempts(self, dbsession):
        match = Match().save()
        game = Game(match_uid=match.uid, index=2).save()
        user = User(email="user@test.project").save()
        question = Question(text="1+1 is = to", position=0, game_uid=game.uid).save()
        Reaction(question=question, user=user, match=match, game_uid=game.uid).save()

        assert match.reactions[0].user == user
        assert match.left_attempts(user) == 0


class TestCaseMatchHash:
    def t_hashMustBeUniqueForEachMatch(self, dbsession, mocker):
        # the first call return a value already used
        random_method = mocker.patch(
            "codechallenge.entities.match.choices",
            side_effect=["LINK-HASH1", "LINK-HASH2"],
        )
        Match(uhash="LINK-HASH1").save()

        MatchHash().get_hash()
        assert random_method.call_count == 2


class TestCaseMatchPassword:
    def t_passwordUniqueForEachMatch(self, dbsession, mocker):
        # the first call return a value already used
        random_method = mocker.patch(
            "codechallenge.entities.match.choices",
            side_effect=["00321", "34550"],
        )
        Match(uhash="AEDRF", password="00321").save()

        MatchPassword(uhash="AEDRF").get_value()
        assert random_method.call_count == 2


class TestCaseMatchCode:
    def t_codeUniqueForEachMatchAtThatTime(self, dbsession, mocker):
        tomorrow = datetime.now() + timedelta(days=1)
        random_method = mocker.patch(
            "codechallenge.entities.match.choices",
            side_effect=["8363", "7775"],
        )
        Match(code=8363, expires=tomorrow).save()

        MatchCode().get_code()
        assert random_method.call_count == 2


class TestCaseGameModel:
    def t_raiseErrorWhenTwoGamesOfMatchHaveSamePosition(self, dbsession):
        new_match = Match().save()
        new_game = Game(index=1, match_uid=new_match.uid).save()
        with pytest.raises((IntegrityError, InvalidRequestError)):
            Game(index=1, match_uid=new_game.match.uid).save()

        dbsession.rollback()

    def t_orderedQuestionsMethod(self, dbsession, emitted_queries):
        match = Match().save()
        game = Game(match_uid=match.uid, index=1).save()
        question_2 = Question(
            text="Where is London?", game_uid=game.uid, position=1
        ).save()
        question_1 = Question(
            text="Where is Lisboa?", game_uid=game.uid, position=0
        ).save()
        question_4 = Question(
            text="Where is Paris?", game_uid=game.uid, position=3
        ).save()
        question_3 = Question(
            text="Where is Berlin?", game_uid=game.uid, position=2
        ).save()

        assert len(emitted_queries) == 7
        assert game.ordered_questions[0] == question_1
        assert game.ordered_questions[1] == question_2
        assert game.ordered_questions[2] == question_3
        assert game.ordered_questions[3] == question_4
        assert len(emitted_queries) == 8


class TestCaseReactionModel:
    def t_cannotExistsTwoReactionsOfTheSameUserAtSameTime(self, dbsession):
        match = Match().save()
        game = Game(match_uid=match.uid, index=0).save()
        user = User(email="user@test.project").save()
        question = Question(text="new-question", position=0, game_uid=game.uid).save()
        answer = Answer(question=question, text="question2.answer1", position=1).save()

        now = datetime.now()
        with pytest.raises((IntegrityError, InvalidRequestError)):
            Reaction(
                match_uid=match.uid,
                question_uid=question.uid,
                answer_uid=answer.uid,
                user_uid=user.uid,
                create_timestamp=now,
                game_uid=game.uid,
            ).save()
            Reaction(
                match_uid=match.uid,
                question_uid=question.uid,
                answer_uid=answer.uid,
                user_uid=user.uid,
                create_timestamp=now,
                game_uid=game.uid,
            ).save()
        dbsession.rollback()

    def t_ifQuestionChangesThenAlsoFKIsUpdatedAndAffectsReaction(self, dbsession):
        match = Match().save()
        game = Game(match_uid=match.uid, index=0).save()
        user = User(email="user@test.project").save()
        question = Question(text="1+1 is = to", position=0).save()
        answer = Answer(question=question, text="2", position=1).save()
        reaction = Reaction(
            match_uid=match.uid,
            question_uid=question.uid,
            answer_uid=answer.uid,
            user_uid=user.uid,
            game_uid=game.uid,
        ).save()
        question.text = "1+2 is = to"
        question.save()

        assert reaction.question.text == "1+2 is = to"

    def t_whenQuestionIsElapsedAnswerIsNotRecorded(self, dbsession):
        match = Match().save()
        game = Game(match_uid=match.uid, index=0).save()
        user = User(email="user@test.project").save()
        question = Question(text="3*3 = ", time=0, position=0).save()
        reaction = Reaction(
            match=match, question=question, user=user, game_uid=game.uid
        ).save()

        answer = Answer(question=question, text="9", position=1).save()
        reaction.record_answer(answer)

        assert reaction.answer is None

    def t_recordAnswerInTime(self, dbsession):
        match = Match().save()
        game = Game(match_uid=match.uid, index=0).save()
        user = User(email="user@test.project").save()
        question = Question(text="1+1 =", time=2, position=0).save()
        reaction = Reaction(
            match=match, question=question, user=user, game_uid=game.uid
        ).save()

        answer = Answer(question=question, text="2", position=1).save()
        reaction.record_answer(answer)

        assert reaction.answer
        assert reaction.answer_time
        # because the score is computed over the response
        # time and this one variates at each tests run
        # isclose is used to avoid brittleness
        assert isclose(reaction.score, 0.999, rel_tol=0.05)

    def t_reactionTimingIsRecordedAlsoForOpenQuestions(self, dbsession):
        match = Match().save()
        game = Game(match_uid=match.uid, index=0).save()
        user = User(email="user@test.project").save()
        question = Question(text="Where is Miami", position=0).save()
        reaction = Reaction(
            match=match, question=question, user=user, game_uid=game.uid
        ).save()

        open_answer = OpenAnswer(text="Florida").save()
        reaction.record_answer(open_answer)
        assert question.is_open
        assert reaction.answer
        assert reaction.answer_time
        # no score should be computed for open questions
        assert not reaction.score

    def t_allReactionsOfUser(self, dbsession):
        match = Match().save()
        game = Game(match_uid=match.uid, index=0).save()
        user = User(email="user@test.project").save()
        q1 = Question(text="t1", position=0).save()
        q2 = Question(text="t2", position=1).save()
        r1 = Reaction(match=match, question=q1, user=user, game_uid=game.uid).save()
        r2 = Reaction(match=match, question=q2, user=user, game_uid=game.uid).save()

        reactions = Reactions.all_reactions_of_user_to_match(
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
