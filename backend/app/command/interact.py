import os
import sys
from pprint import pprint

import requests
import typer

app = typer.Typer()


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
    text = input("Text: ")
    payload = {"text": text}
    position = input("Position ")
    payload["position"] = position

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
    payload = {
        "name": "Wednesday match n.1",
        "with_code": True,
        "times": 0,
        "from_time": "2023-05-21T06:19:43.780Z",
        "to_time": "2023-05-22T06:19:43.780Z",
        "is_restricted": False,
        "order": True,
        "questions": [
            {
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
                "time": 0,
                "content_url": "string",
            },
        ],
    }
    result = client.post(f"{BASE_URL}/matches/new", json=payload)
    typer.echo((result.status_code, result.json()))


def list_questions():
    client = Client()
    client.authenticate()
    response = client.get(f"{BASE_URL}/questions/", params={})
    if response.ok:
        for question in response.json()["questions"]:
            typer.echo(pprint(question))
    else:
        typer.echo(response.reason)


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
        }.get(user_choice)
        if not action:
            exit_command()

        action()


if __name__ == "__main__":
    app()
