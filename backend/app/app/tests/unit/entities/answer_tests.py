import pytest


class TestCaseAnswer:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session, question_dto, answer_dto, match_dto):
        self.question_dto = question_dto
        self.answer_dto = answer_dto

    def t_textIsCorrectlyParsed(self):
        question = self.question_dto.new(text="US has 40 states?", position=0)
        self.question_dto.save(question)
        ans = self.answer_dto.new(
            question_uid=question.uid, text=False, position=0, is_correct=True
        )
        self.answer_dto.save(ans)
        assert ans.text == "False"
        assert ans.boolean
