from datetime import datetime, timedelta

import pytest

from app.constants import MATCH_HASH_LEN, MATCH_PASSWORD_LEN
from app.domain_service.data_transfer.match import MatchCode, MatchHash, MatchPassword
from app.exceptions import NotUsableQuestionError


class TestCaseMatchModel:
    def test_1(self, match_dto, game_dto, question_dto):
        """verify match.questions property"""
        match = match_dto.save(match_dto.new())
        first_game = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(first_game)
        question = question_dto.new(
            text="Where is London?",
            game_uid=first_game.uid,
            position=0,
        )
        question_dto.save(question)
        second_game = game_dto.new(match_uid=match.uid, index=1)
        game_dto.save(second_game)

        question = question_dto.new(
            text="Where is Vienna?",
            game_uid=second_game.uid,
            position=0,
        )
        question_dto.save(question)
        assert match.questions[0][0].text == "Where is London?"
        assert match.questions[0][0].game == first_game
        assert match.questions[1][0].text == "Where is Vienna?"
        assert match.questions[1][0].game == second_game

    def test_2(self, match_dto):
        """Create a new match with hash"""
        match = match_dto.save(match_dto.new(with_code=False))
        assert match.uhash is not None
        assert len(match.uhash) == MATCH_HASH_LEN

    def test_3(self, match_dto):
        """Create a restricted match"""
        match = match_dto.save(match_dto.new(is_restricted=True))
        assert match.uhash
        assert len(match.password) == MATCH_PASSWORD_LEN

    def test_4(self, match_dto, game_dto, question_dto):
        """Update the text of a question of the match"""
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(question)

        n = question_dto.count()
        match_dto.update_questions(
            match,
            [
                {
                    "uid": question.uid,
                    "text": "What is the capital of Norway?",
                }
            ],
        )
        no_new_questions = n == question_dto.count()
        assert no_new_questions
        assert question.text == "What is the capital of Norway?"

    def test_5(self, match_dto, question_dto, answer_dto):
        """Import existing template question to a match"""
        question_1 = question_dto.new(text="Where is London?", position=0)
        question_2 = question_dto.new(text="Where is Vienna?", position=1)
        question_dto.add_many([question_1, question_2])

        answer = answer_dto.new(
            question_uid=question_1.uid,
            text="question2.answer1",
            position=1,
        )
        answer_dto.save(answer)

        new_match = match_dto.save(match_dto.new(with_code=False))
        questions_cnt = question_dto.count()
        answers_cnt = answer_dto.count()
        match_dto.import_template_questions(new_match, [question_1.uid, question_2.uid])
        assert question_dto.count() == questions_cnt + 2
        assert answer_dto.count() == answers_cnt + 0

    def test_6(self, match_dto, game_dto, question_dto):
        """
        GIVEN: one question already linked to a game of a match
        WHEN: it's about to be imported to another match
        THEN: an error should be raised
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=3,
        )
        question_dto.save(question)
        with pytest.raises(NotUsableQuestionError):
            match_dto.import_template_questions(match, [question.uid])

    def test_8(self, match_dto, game_dto, question_dto):
        """move one question from one game to another one"""
        match = match_dto.save(match_dto.new())
        first_game = game_dto.new(match_uid=match.uid, index=0)
        game_dto.save(first_game)
        second_game = game_dto.new(match_uid=match.uid, index=1)
        game_dto.save(second_game)
        question_1 = question_dto.new(
            text="Where is London?",
            game_uid=first_game.uid,
            position=0,
        )
        question_dto.save(question_1)
        question_2 = question_dto.new(
            text="Where is New York?",
            game_uid=first_game.uid,
            position=1,
        )
        question_dto.save(question_2)
        question_3 = question_dto.new(
            text="Where is Tokyo?",
            game_uid=second_game.uid,
            position=1,
        )
        question_dto.save(question_3)
        data = {"questions": [{"uid": question_1.uid, "game_uid": second_game.uid}]}
        match_dto.update(match, **data)
        assert question_1.game == second_game

    def test_9(self, match_dto, game_dto):
        """Update the order property of a game"""
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        data = {"games": [{"uid": game.uid, "order": False}]}
        match_dto.update(match, **data)
        assert not game.order

    def test_10(self, match_dto, reaction_dto, game_dto, question_dto, user_dto):
        """
        GIVEN: a match that can be played only once
        WHEN: a user plays to it
        THEN: no other attempts should be left to him
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        question = question_dto.new(text="1+1 is = to", position=0, game_uid=game.uid)
        question_dto.save(question)
        reaction_dto.save(
            reaction_dto.new(
                question=question,
                user=user,
                match=match,
                game_uid=game.uid,
            )
        )

        assert match.reactions[0].user == user
        assert match.left_attempts(user) == 0

    def test_11(self, match_dto, game_dto, user_dto, question_dto, reaction_dto):
        """
        GIVEN: a match already started once
        WHEN: the user wants to start
        THEN: the user should be able to do it indefinitely because
                because the times parameter of the match is 0
        """
        match = match_dto.new(times=0)
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        question = question_dto.new(text="1+1 is = to", position=0, game_uid=game.uid)
        question_dto.save(question)
        reaction_dto.save(
            reaction_dto.new(
                question=question,
                user=user,
                match=match,
                game_uid=game.uid,
            )
        )

        assert match.reactions[0].user == user
        assert match.left_attempts(user) == 1

    def test_12(self, match_dto, game_dto):
        """adding two boolean question to one game"""
        questions = [
            {
                "answers": [{"text": True}, {"text": False}],
                "text": "There is no cream in the traditional Carbonara?",
            },
        ]
        match = match_dto.save(match_dto.new())
        first_game = game_dto.save(game_dto.new(match_uid=match.uid, index=0))
        match_dto.insert_questions(match, questions, game_uid=first_game.uid)

        assert match.questions[0][0].boolean
        assert match.questions[0][0].game_uid == first_game.uid

        assert match.questions[0][0].answers_list[0]["boolean"]
        assert match.questions[0][0].answers_list[0]["text"] == "True"
        assert match.questions[0][0].answers_list[0]["is_correct"]
        assert not match.questions[0][0].answers_list[1]["is_correct"]

        second_game = game_dto.save(game_dto.new(match_uid=match.uid, index=1))
        questions = [
            {
                "answers": [{"text": False}, {"text": True}],
                "text": "Biscuits are the same in the US and in the UK?",
            },
        ]
        match_dto.insert_questions(match, questions, game_uid=second_game.uid)

        assert match.questions[1][0].game_uid == second_game.uid
        assert match.questions[1][0].answers_list[1]["boolean"]
        assert match.questions[1][0].answers_list[0]["text"] == "False"
        assert match.questions[1][0].answers_list[0]["is_correct"]

    def test_13(self, match_dto, game_dto):
        """
        GIVEN: one question added to a specific game of a match
        WHEN: another question is added using the same method, but
                without specifying the game
        THEN: it should be added to the same existing game
        """
        match = match_dto.save(match_dto.new())
        first_game = game_dto.save(game_dto.new(match_uid=match.uid, index=0))
        questions = [
            {
                "answers": [{"text": False}, {"text": True}],
                "text": "Question.1",
            },
        ]
        match_dto.insert_questions(match, questions, game_uid=first_game.uid)
        assert match.questions[0][0].game_uid == first_game.uid

        questions = [
            {
                "answers": [{"text": False}, {"text": True}],
                "text": "Question.2",
            },
        ]
        match_dto.insert_questions(match, questions)
        assert match.questions[0][1].game_uid == first_game.uid


class TestCaseMatchHash:
    def test_1(self, db_session, mocker, match_dto):
        """guarantee that match's hash is randomly generated
        each time a match is created
        """
        random_method = mocker.patch(
            "app.domain_service.data_transfer.match.choices",
            side_effect=["LINK-HASH1", "LINK-HASH2"],
        )
        match_dto.save(match_dto.new(uhash="LINK-HASH1"))

        MatchHash(db_session=db_session).get_hash()
        assert random_method.call_count == 2


class TestCaseMatchPassword:
    def test_1(self, db_session, mocker, match_dto):
        """guarantee that match's password (if any) is randomly
        generated each time a match is created
        """
        random_method = mocker.patch(
            "app.domain_service.data_transfer.match.choices",
            side_effect=["00321", "34550"],
        )
        match_dto.save(match_dto.new(uhash="AEDRF", password="00321"))

        MatchPassword(uhash="AEDRF", db_session=db_session).get_value()
        assert random_method.call_count == 2


class TestCaseMatchCode:
    def test_1(self, db_session, mocker, match_dto):
        """guarantee that match's code is randomly generated
        each time a match is created
        """
        tomorrow = datetime.now() + timedelta(days=1)
        random_method = mocker.patch(
            "app.domain_service.data_transfer.match.choices",
            side_effect=["8363", "7775"],
        )
        match_dto.save(match_dto.new(code=8363, expires=tomorrow))

        MatchCode(db_session=db_session).get_code()
        assert random_method.call_count == 2
