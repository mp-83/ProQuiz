import pytest
from sqlalchemy.exc import IntegrityError, InvalidRequestError


class TestCaseQuestion:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session, question_dto, answer_dto, match_dto):
        self.question_dto = question_dto
        self.answer_dto = answer_dto
        self.match_dto = match_dto

    @pytest.fixture
    def samples(self):
        self.question_dto.add_many(
            [
                self.question_dto.new(text="q1.text", position=0),
                self.question_dto.new(text="q2.text", position=1),
                self.question_dto.new(text="q3.text", position=2),
            ]
        )
        yield

    def t_theQuestionAtPosition(self, samples):
        question = self.question_dto.at_position(0)
        assert question.text == "q1.text"
        assert question.create_timestamp is not None

    def t_newCreatedAnswersShouldBeAvailableFromTheQuestion(self, samples):
        question = self.question_dto.get(position=0)
        answer = self.answer_dto.new(
            question=question,
            text="question2.answer1",
            position=1,
        )
        self.answer_dto.save(answer)
        answer = self.answer_dto.new(
            question=question,
            text="question2.answer2",
            position=2,
        )
        self.answer_dto.save(answer)
        assert self.answer_dto.count() == 2
        assert question.answers[0].question_uid == question.uid

    def t_createQuestionWithoutPosition(self, samples):
        new_question = self.question_dto.new(text="new-question", position=1)
        self.question_dto.save(new_question)
        assert new_question.is_open
        assert new_question.is_template

    def t_allAnswersOfAQuestionMustDiffer(self, samples, db_session):
        question = self.question_dto.get(position=1)
        with pytest.raises((IntegrityError, InvalidRequestError)):
            question.answers.extend(
                [
                    self.answer_dto.new(text="question2.answer1", position=1),
                    self.answer_dto.new(text="question2.answer1", position=2),
                ]
            )
            self.question_dto.save(question)

        db_session.rollback()

    def t_createManyAnswersAtOnce(self):
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
        new_question = self.question_dto.new(
            text=data["text"], position=data["position"]
        )
        self.question_dto.create_with_answers(new_question, data["answers"])

        expected = {e["text"] for e in data["answers"]}
        assert new_question
        assert {e.text for e in new_question.answers} == expected
        assert self.answer_dto.get(text="The machine was undergoing repair").is_correct
        assert self.answer_dto.get(text="The machine was undergoing repair").level == 1

    def t_cloningQuestion(self):
        new_question = self.question_dto.new(text="new-question", position=0)
        self.question_dto.save(new_question)
        answer = self.answer_dto.new(
            question_uid=new_question.uid,
            text="The machine was undergoing repair",
            position=0,
        )
        self.answer_dto.save(answer)
        cloned = self.question_dto.clone(new_question)
        assert new_question.uid != cloned.uid
        assert new_question.answers[0] != cloned.answers[0]

    def t_questionsAnswersAreOrderedByDefault(self):
        # the reverse relation fields .answers is ordered by default
        question = self.question_dto.new(text="new-question", position=0)
        self.question_dto.save(question)
        answer = self.answer_dto.new(
            question_uid=question.uid, text="Answer1", position=0
        )
        self.answer_dto.save(answer)
        answer = self.answer_dto.new(
            question_uid=question.uid, text="Answer2", position=1
        )
        self.answer_dto.save(answer)

        assert question.answers[0].text == "Answer1"
        assert question.answers[0].level == 1
        assert question.answers[1].text == "Answer2"

    def t_updateLevelOfOneAnswerAndTextOfAnother(self):
        question = self.question_dto.new(text="new-question", position=0)
        self.question_dto.save(question)
        a1 = self.answer_dto.new(
            question_uid=question.uid, text="False", position=0, level=1
        )
        self.answer_dto.save(a1)
        a2 = self.answer_dto.new(
            question_uid=question.uid, text="True", position=1, level=0
        )
        self.answer_dto.save(a2)

        ans_1_data = a1.json
        ans_1_data.update(level=2)

        ans_2_data = a2.json
        ans_2_data.update(level=1)

        self.question_dto.update_answers(question, [ans_1_data, ans_2_data])
        assert question.answers_by_position[0].level == 2

        assert question.answers_by_position[1].level == 1

        assert question.answers_by_position[0].text == "False"
