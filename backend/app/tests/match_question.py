import os

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

    def authenticate(self, username, password):
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


@app.command()
def rankings(match_uid: str):
    client = Client()
    result = client.get(f"{BASE_URL}/players/{match_uid}")
    typer.echo(result.json())


@app.command()
def new_match():
    client = Client()
    client.authenticate(
        username=os.getenv("FIRST_SUPERUSER"),
        password=os.getenv("FIRST_SUPERUSER_PASSWORD"),
    )
    payload = {
        "name": "Sunday match n.2",
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


if __name__ == "__main__":
    app()
