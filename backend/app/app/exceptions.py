class BaseException(Exception):
    def __init__(self, message="", *args):
        super(Exception).__init__(*args)
        self._message = message

    @property
    def message(self):
        return self._message


class InternalException(BaseException):
    """"""


class MatchOver(BaseException):
    """"""


class NotUsableQuestionError(InternalException):
    """"""


class MatchError(InternalException):
    """"""


class MatchNotPlayableError(InternalException):
    """Match has been played by the user more than match.times"""


class GameError(InternalException):
    """Generic exception occuring during Match"""


class GameOver(InternalException):
    """"""


class ValidateError(InternalException):
    """"""


class NotFoundObjectError(InternalException):
    """"""
