from string import ascii_letters, digits

MATCH_HASH_LEN = 5
HASH_POPULATION = ascii_letters
MATCH_PASSWORD_LEN = 5
PASSWORD_POPULATION = digits
MATCH_CODE_LEN = 4
CODE_POPULATION = digits
ATTEMPT_UID_LENGTH = 32
ATTEMPT_UID_POPULATION = "abcdef" + digits

ISOFORMAT = "%Y-%m-%dT%H:%M:%S.%f"

MATCH_NAME_MAX_LENGTH = 100
TOPIC_NAME_LENGTH = 60

URL_LENGTH = 256

QUESTION_TEXT_MIN_LENGTH = 4
QUESTION_TEXT_MAX_LENGTH = 500
ANSWER_TEXT_MAX_LENGTH = 500
OPEN_ANSWER_TEXT_MAX_LENGTH = 2000

EMAIL_MAX_LENGTH = 256
DIGEST_SIZE = 16
DIGEST_LENGTH = 32
KEY_LENGTH = 32
USER_NAME_MAX_LENGTH = 30
# no matter the password's length,
# the hash length stays the same
PASSWORD_HASH_LENGTH = 60
