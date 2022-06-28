import pytest
from sqlalchemy.exc import IntegrityError, InvalidRequestError


class TestCaseAnswer:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session, question_dto, answer_dto, match_dto):
        self.question_dto = question_dto
        self.answer_dto = answer_dto

    def t_noSameBooleanAnswers(self, db_session):
        question = self.question_dto.new(text="US has 40 states?", position=0)
        self.question_dto.save(question)
        ans = self.answer_dto.new(
            question_uid=question.uid, bool_value=False, position=0, is_correct=True
        )
        self.answer_dto.save(ans)
        with pytest.raises((IntegrityError, InvalidRequestError)):
            ans = self.answer_dto.new(
                question_uid=question.uid, bool_value=False, position=0, is_correct=True
            )
            self.answer_dto.save(ans)

        db_session.rollback()

    # DOES NOT WORK WITH IN-MEMORY DATABASE
    # def t_eitherTextOrBoolValue(self, db_session):
    #     question = self.question_dto.new(text="US has 40 states?", position=0)
    #     self.question_dto.save(question)
    #     ans = self.answer_dto.new(question_uid=question.uid, bool_value=False, position=0, is_correct=True)
    #     self.answer_dto.save(ans)
    #     with pytest.raises((IntegrityError, InvalidRequestError)):
    #         ans = self.answer_dto.new(question_uid=question.uid, text="yes", position=0, is_correct=True)
    #         self.answer_dto.save(ans)
    #
    #     db_session.rollback()
