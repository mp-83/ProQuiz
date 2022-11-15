class TestCaseAnswer:
    def test_1(self, question_dto, answer_dto):
        """Verify that boolean value for text, are correctly parsed"""
        question = question_dto.new(text="US has 40 states?", position=0)
        question_dto.save(question)
        ans = answer_dto.new(
            question_uid=question.uid, text=False, position=0, is_correct=True
        )
        answer_dto.save(ans)
        assert ans.text == "False"
        assert ans.boolean
