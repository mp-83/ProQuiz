from app.exceptions import ValidateError


class ValidateNewQuestion:
    def __init__(self, question_in: dict):
        self.text = question_in.get("text")
        self.content_url = question_in.get("content_url")

    def either_text_or_content(self):
        if not (self.text or self.content_url):
            raise ValidateError("Either text or contentURL must be provided ")

    def is_valid(self):
        self.either_text_or_content()
