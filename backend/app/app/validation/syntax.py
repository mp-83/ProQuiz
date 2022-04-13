import re
from base64 import b64decode
from datetime import datetime

import yaml
from app.constants import (
    CODE_POPULATION,
    HASH_POPULATION,
    ISOFORMAT,
    MATCH_CODE_LEN,
    MATCH_HASH_LEN,
    MATCH_PASSWORD_LEN,
    PASSWORD_POPULATION,
)

land_play_schema = {
    "match_uhash": {
        "type": "string",
        "required": True,
        "regex": "[" + f"{HASH_POPULATION}" + "]{" + f"{MATCH_HASH_LEN}" + "}",
    }
}


code_play_schema = {
    "match_code": {
        "type": "string",
        "required": True,
        "regex": "[" + f"{CODE_POPULATION}" + "]{" + f"{MATCH_CODE_LEN}" + "}",
    }
}


start_play_schema = {
    "match_uid": {"type": "integer", "coerce": int, "required": True, "min": 1},
    "user_uid": {"type": "integer", "coerce": int, "min": 1},
    "password": {
        "type": "string",
        "regex": "[" + f"{PASSWORD_POPULATION}" + "]{" + f"{MATCH_PASSWORD_LEN}" + "}",
    },
}

next_play_schema = {
    "match_uid": {"type": "integer", "coerce": int, "required": True, "min": 1},
    "user_uid": {"type": "integer", "coerce": int, "required": True, "min": 1},
    "answer_uid": {"type": "integer", "coerce": int, "required": True, "min": 1},
    "question_uid": {"type": "integer", "coerce": int, "required": True, "min": 1},
}


def check_date(field, value, error):
    if value is None:
        return

    try:
        datetime.strptime(value, "%d%m%Y")
    except ValueError:
        error(field, "Invalid data format")


sign_play_schema = {
    "email": {
        "type": "string",
        "required": True,
        "regex": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]{2,}\.[a-zA-Z]{2,}",
        "maxlength": 30,
    },
    "token": {
        "type": "string",
        "required": True,
        "minlength": 8,
        "maxlength": 8,
        "check_with": check_date,
    },
}

create_question_schema = {
    "game_uid": {"type": "integer", "coerce": int, "required": False},
    "text": {"type": "string", "required": True, "maxlength": 400},
    "position": {"type": "integer", "coerce": int, "required": True},
    "time": {"type": "integer", "coerce": int},
    "content_url": {"type": "string", "coerce": str},
    "code": {"type": "string", "coerce": str},
    "answers": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {"text": {"type": "string", "required": True}},
        },
    },
}

edit_question_schema = {
    "game_uid": {"type": "integer", "coerce": int, "required": False},
    "text": {"type": "string", "maxlength": 400},
    "position": {"type": "integer", "coerce": int, "min": 0},
    "time": {"type": "integer", "coerce": int},
    "content_url": {"type": "string", "coerce": str},
    "code": {"type": "string", "coerce": str},
    "answers": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "uid": {"type": "integer", "coerce": int, "required": False},
                "text": {"type": "string", "required": True},
            },
        },
    },
}


def coerce_order(value):
    if value in ["false", "False", False]:
        return False
    elif value in ["true", "True", True]:
        return True
    return None


def coerce_times(value):
    if value == "null":
        return None
    return value


def coerce_datetime_isoformat(value):
    try:
        return datetime.strptime(value, ISOFORMAT)
    except (ValueError, TypeError):
        return


create_match_schema = {
    "name": {"type": "string"},
    "with_code": {"type": "boolean", "coerce": bool},
    "times": {
        "type": "integer",
        "coerce": (
            coerce_times,
            int,
        ),  # coerce callables are executed according to the order they are in the tuple
        "min": 1,
        "nullable": True,
    },
    "from_time": {"type": "datetime", "coerce": coerce_datetime_isoformat},
    "to_time": {"type": "datetime", "coerce": coerce_datetime_isoformat},
    "is_restricted": {"type": "boolean", "coerce": bool},
    "order": {"type": "boolean", "coerce": coerce_order},
    "questions": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "text": {"type": "string", "required": True},
                "answers": {
                    "type": "list",
                    "schema": {
                        "type": "dict",
                        "schema": {"text": {"type": "string", "required": True}},
                    },
                },
            },
        },
    },
}


edit_match_schema = {
    "name": {"type": "string"},
    "times": {"type": "integer", "coerce": int, "min": 1, "nullable": True},
    "is_restricted": {"type": "boolean", "coerce": bool},
    "order": {"type": "boolean", "coerce": coerce_order},
    "questions": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "text": {"type": "string"},
                "game": {"type": "integer", "coerce": int, "min": 0},
                "answers": {
                    "type": "list",
                    "schema": {"type": "dict", "schema": {"text": {"type": "string"}}},
                },
            },
        },
    },
}


user_login_schema = {
    "email": {
        "type": "string",
        "required": True,
        "regex": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]{2,}\.[a-zA-Z]{2,}",
        "maxlength": 30,
    },
    "password": {"type": "string", "required": True, "minlength": 8, "maxlength": 100},
}


player_list_schema = {
    "match_uid": {"type": "integer", "coerce": int, "required": True, "min": 1},
}


match_rankings_schema = {
    "match_uid": {"type": "integer", "coerce": int, "required": True, "min": 1},
}


def coerce_yaml_content(value):
    if not value:
        return ""

    try:
        return yaml.load(value, yaml.Loader)
    except yaml.scanner.ScannerError:
        return ""


def coerce_to_b64content(value):
    b64content = re.sub(r"data:application/x-yaml;base64,", "", value)
    return b64decode(b64content)


def to_expected_mapping(value):
    result = {"questions": []}
    question = {}
    for i, elem in enumerate(value.get("questions")):
        if i % 2 == 0:
            question["text"] = elem
        else:
            question["answers"] = [{"text": text} for text in elem["answers"]]
            result["questions"].append(question)
            question = {}
    return result


match_yaml_import_schema = {
    "match_uid": {"type": "integer", "coerce": int, "required": True, "min": 1},
    "data": {
        "type": "dict",
        "required": True,
        "coerce": (coerce_to_b64content, coerce_yaml_content, to_expected_mapping),
        "schema": {
            "questions": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "text": {"type": "string", "required": True},
                        "answers": {
                            "type": "list",
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "text": {"type": "string", "required": True}
                                },
                            },
                        },
                    },
                },
            }
        },
    },
}
