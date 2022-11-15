import pytest
from sqlalchemy.exc import IntegrityError, InvalidRequestError


class TestCaseQuestion:
    @pytest.fixture
    def samples(self, question_dto):
        question_dto.add_many(
            [
                question_dto.new(text="q1.text", position=0),
                question_dto.new(text="q2.text", position=1),
                question_dto.new(text="q3.text", position=2),
            ]
        )
        yield

    def test_1(self, samples, question_dto):
        question = question_dto.at_position(0)
        assert question.text == "q1.text"
        assert question.create_timestamp is not None

    def test_2(self, samples, question_dto, answer_dto):
        """answers can be retrieved via question"""
        question = question_dto.get(position=0)
        answer = answer_dto.new(
            question=question,
            text="question2.answer1",
            position=1,
        )
        answer_dto.save(answer)
        answer = answer_dto.new(
            question=question,
            text="question2.answer2",
            position=2,
        )
        answer_dto.save(answer)
        assert answer_dto.count() == 2
        assert question.answers[0].question_uid == question.uid

    def test_3(self, samples, question_dto):
        new_question = question_dto.new(text="new-question", position=0)
        question_dto.save(new_question)
        assert new_question.is_open
        assert new_question.is_template

    def test_4(self, samples, match_dto, game_dto, question_dto):
        """
        GIVEN: an existing question associated to a game
        WHEN: it is updated and the game is set to None
        THEN: it becomes a template question
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid, order=False)
        game_dto.save(game)
        new_question = question_dto.new(
            text="new-question", position=1, game_uid=game.uid
        )
        question_dto.save(new_question)

        question_dto.update(new_question, {"game": None})
        assert new_question.is_template

    def test_5(self, samples, db_session, question_dto, answer_dto):
        """a question cannot have two answers with same text"""
        question = question_dto.get(position=1)
        answer = answer_dto.new(
            text="Where is Manchester?", position=1, question_uid=question.uid
        )
        answer_dto.save(answer)
        with pytest.raises((IntegrityError, InvalidRequestError)):
            answer = answer_dto.new(
                text="Where is Manchester?", position=2, question_uid=question.uid
            )
            answer_dto.save(answer)

        db_session.rollback()

    def test_6(self, question_dto, answer_dto):
        """create many answers at once"""
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
        new_question = question_dto.new(text=data["text"], position=data["position"])
        question_dto.create_with_answers(new_question, data["answers"])

        expected = {e["text"] for e in data["answers"]}
        assert new_question
        assert {e.text for e in new_question.answers} == expected
        assert answer_dto.get(text="The machine was undergoing repair").is_correct
        assert answer_dto.get(text="The machine was undergoing repair").level == 1

    def test_7(self, question_dto, answer_dto):
        """cloning one questions"""
        new_question = question_dto.new(text="new-question", position=0)
        question_dto.save(new_question)
        answer = answer_dto.new(
            question_uid=new_question.uid,
            text="The machine was undergoing repair",
            position=0,
        )
        answer_dto.save(answer)
        cloned = question_dto.clone(new_question)
        assert new_question.uid != cloned.uid
        assert new_question.answers[0] != cloned.answers[0]
        assert new_question.answers[0].text == cloned.answers[0].text

    def test_8(self, question_dto, answer_dto):
        """Simultaneously update different fields of different answers"""
        question = question_dto.new(text="new-question", position=0)
        question_dto.save(question)
        a1 = answer_dto.new(
            question_uid=question.uid, text="False", position=0, level=1
        )
        answer_dto.save(a1)
        a2 = answer_dto.new(question_uid=question.uid, text="True", position=1, level=0)
        answer_dto.save(a2)

        ans_1_data = a1.json
        ans_1_data.update(level=2)

        ans_2_data = a2.json
        ans_2_data.update(level=1)

        question_dto.update_answers(question, [ans_1_data, ans_2_data])
        assert question.answers_by_position[0].level == 2
        assert question.answers_by_position[1].level == 1
        assert question.answers_by_position[0].text == "False"
