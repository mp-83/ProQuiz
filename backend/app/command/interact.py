import logging
import os
import sys
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pprint import pprint

import requests
import typer

logger = logging.getLogger(__name__)

app = typer.Typer()


"""
alias quiz='clear && docker-compose exec backend python command/interact.py'
"""

BASE_URL = "http://localhost:7070/api/v1"


class TestingError(Exception):
    def __init__(self, message="", *args):
        super(Exception).__init__(*args)
        self._message = message

    @property
    def message(self):
        return self._message


class Client:
    def __init__(self):
        self._client = requests.Session()

    def authenticate(self, username=None, password=None):
        username = username or os.getenv("FIRST_SUPERUSER")
        password = password or os.getenv("FIRST_SUPERUSER_PASSWORD")
        if "Authorization" in self._client.headers:
            return

        logger.info(f"Authenticating user: {username}")
        response = self._client.post(
            f"{BASE_URL}/login/access-token",
            data={"username": username, "password": password},
        )
        if not response.ok:
            raise TestingError(f"{response.json()}")
        token = response.json().get("access_token")
        self._client.headers.update(**{"Authorization": f"Bearer {token}"})
        return self

    def post(self, *args, **kwargs):
        return self._client.post(*args, **kwargs)

    def put(self, *args, **kwargs):
        return self._client.put(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._client.get(*args, **kwargs)


def list_matches():
    client = Client()
    client.authenticate()
    result = client.get(f"{BASE_URL}/matches")
    for match in result.json().values():
        typer.echo(pprint(match))


def match_details():
    typer.echo("Enter the match ID")
    match_uid = input()
    client = Client()
    client.authenticate()
    result = client.get(f"{BASE_URL}/matches/{match_uid}")
    typer.echo(pprint(result.json()))


def new_question():
    text = input("Text ==> ")
    payload = {"text": text}

    position = input("Position ==> ")
    payload["position"] = position

    answers = []
    while True:
        answer_text = input("Answer text ==> ")
        if answer_text == "":
            break
        answers.append({"text": answer_text})

    payload["answers"] = answers

    client = Client()
    client.authenticate()
    response = client.post(f"{BASE_URL}/questions/new", json=payload)
    if response.ok:
        typer.echo(pprint(response.json()))
    else:
        typer.echo(response.reason)


def new_match():
    client = Client()
    client.authenticate()
    name = input("Match name ==> ")
    with_code = input("With code? y/n ==> ")
    with_code = with_code == "y"

    is_restricted = input("Is restricted? y/n ==> ")
    is_restricted = is_restricted == "y"

    order = input("Order? y/n ==> ")
    order = order == "y"

    payload = {
        "name": name,
        "with_code": with_code,
        "times": 1,
        "from_time": (datetime.now(tz=timezone.utc) + timedelta(minutes=1)).isoformat(),
        "to_time": (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat(),
        "is_restricted": is_restricted,
        "order": order,
    }
    result = client.post(f"{BASE_URL}/matches/new", json=payload)
    typer.echo((result.status_code, result.json()))


def list_questions():
    client = Client()
    client.authenticate()
    match_uid = input("Match ID: ")
    match_uid = None if match_uid == "" else int(match_uid)
    response = client.get(f"{BASE_URL}/questions/", params={"match_uid": match_uid})
    if response.ok:
        for question in response.json()["questions"]:
            typer.echo(pprint(question))
    else:
        typer.echo(response.reason)


def upload_yaml():
    client = Client()
    client.authenticate()

    if input("Create a new match?  ") == "y":
        new_match()

    # the file must reside anywhere under proquiz/backend/app/
    file_path = input("File path /proquiz/backend/app ==> ")
    match_uid = input("The Match UID ==> ")

    with open(file_path, "rb") as fp:
        b64content = b64encode(fp.read()).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"

        payload = {"uid": match_uid, "data": b64string}
        result = client.post(f"{BASE_URL}/matches/yaml_import", json=payload)
        typer.echo((result.status_code, result.json()))


def exit_command():
    typer.echo("Exiting")
    sys.exit(0)


def menu():
    main_message = """
    Choose your option:
        1. list matches
        2. get match details
        3. create a new match
        4. create new question
        5. list all questions
        6. upload quiz from YAML file
        Enter to exit
    """
    typer.echo(main_message)
    return input()


@app.command()
def start():
    while True:
        user_choice = menu()
        action = {
            "1": list_matches,
            "2": match_details,
            "3": new_match,
            "4": new_question,
            "5": list_questions,
            "6": upload_yaml,
        }.get(user_choice)
        if not action:
            exit_command()

        action()


if __name__ == "__main__":
    app()
