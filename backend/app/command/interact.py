import logging
import os
import select
import sys
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pprint import pprint
from time import sleep

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


def list_matches(client):
    result = client.get(f"{BASE_URL}/matches/")
    typer.echo("\nMATCHES \n\n")
    for match in result.json()["matches"]:
        mm_substr = (
            "[MM]"
            if len(match["games_list"]) > 1 and "[multi-game]" not in match["name"]
            else ""
        )
        if match["uhash"]:
            substr = (
                f"Password {match['password']}"
                if match["is_restricted"]
                else "W/Out password"
            )
            msg = f"{match['name']} {mm_substr}:: ID {match['uid']} :: {len(match['questions_list'])} Questions :: Hash {match['uhash']} :: {substr}"
        else:
            msg = f"{match['name']} {mm_substr}:: ID {match['uid']} :: {len(match['questions_list'])} Questions :: Code {match['code']}"
        typer.echo(f"{msg}")


def new_match(client):
    name = input("Match name ==> ")
    with_code = input("With code? y/n ==> ")
    with_code = with_code == "y"

    is_restricted = input("Is restricted? y/n ==> ")
    is_restricted = is_restricted == "y"

    order = input("Order? y/n ==> ")
    order = order == "y"
    from_time = input("Active from date (YYYY-MM-DD): ")
    if from_time:
        from_time += "T00:01:00+00:00"
    else:
        from_time = (datetime.now(tz=timezone.utc) + timedelta(minutes=1)).isoformat()

    to_time = input("Expiration (YYYY-MM-DD): ")
    if to_time:
        to_time += "T23:59:00+00:00"
    else:
        to_time = (datetime.now(tz=timezone.utc) + timedelta(days=100)).isoformat()

    payload = {
        "name": name,
        "with_code": with_code,
        "times": 1,
        "from_time": from_time,
        "to_time": to_time,
        "is_restricted": is_restricted,
        "order": order,
    }
    response = client.post(f"{BASE_URL}/matches/new", json=payload)
    if response.status_code in [200, 422, 400]:
        typer.echo(pprint(response.json()))
    else:
        typer.echo(f"ERROR: {response.reason}")


def match_details(client):
    match_uid = input("Enter the match ID:  ")
    with_out_questions = (
        input("Only match's details W/OUT questions and answers: y/n ==> ") == "y"
    )
    response = client.get(f"{BASE_URL}/matches/{match_uid}")
    if not response.ok:
        typer.echo(f"ERROR: {response.reason}")
        return

    details = response.json().copy()
    if with_out_questions:
        details.pop("questions_list")
    typer.echo(pprint(details))
    return response.json()


def edit_match(client):
    current_match = match_details(client)
    if not current_match:
        return
    match_uid = current_match["uid"]

    name = input("Name: ") or current_match["name"]
    times = input("Times: ") or current_match["times"]
    order = input("Order: ") or current_match["order"]
    password = input("Password: ") or current_match["password"]
    from_time = input("Active from date (YYYY-MM-DD): ")
    if from_time:
        from_time += "T00:01:00"
    else:
        from_time = current_match["from_time"]

    to_time = input("Expiration (YYYY-MM-DD): ")
    if to_time:
        to_time += "T23:59:00"
    else:
        to_time = current_match["expires"]

    payload = {
        "name": name,
        "times": times,
        "order": order,
        "password": password,
        "to_time": to_time,
        "from_time": from_time,
    }

    typer.echo("Updating Match")
    response = client.put(f"{BASE_URL}/matches/edit/{match_uid}", json=payload)
    if response.status_code in [200, 422, 400]:
        typer.echo(pprint(response.json()))
    else:
        typer.echo(f"ERROR: {response.reason}")


def new_question(client):
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

    response = client.post(f"{BASE_URL}/questions/new", json=payload)
    if response.status_code in [200, 422, 400]:
        typer.echo(pprint(response.json()))
    else:
        typer.echo(response.reason)


def question_details(client):
    question_uid = input("ID of the question to edit:  ")
    response = client.get(f"{BASE_URL}/questions/{question_uid}")
    if not response.ok:
        typer.echo(f"{response.status_code}: {response.reason}")
        return

    pprint(response.json())
    typer.echo(f"\n\nQuestion ID => {question_uid}")
    return response.json()


def edit_answers_of_question(client):
    typer.echo("This function only edits the answers of a questions")
    # Retrieve current question
    current_match = match_details(client)
    if not current_match:
        return

    current_status = question_details(client)
    if not current_status:
        return

    question_uid = current_status["uid"]
    answers = current_status["answers_list"]
    answer_uid = input("Enter answer UID: ")
    position, current_answer = [
        (pos, ans) for pos, ans in enumerate(answers) if ans["uid"] == int(answer_uid)
    ][0]

    change_pos = input("Change position? y/n ") == "y"
    if change_pos:
        new_pos_no = input("New position: ")
        data = answers.pop(position)
        answers.insert(int(new_pos_no), data)

    response = client.put(
        f"{BASE_URL}/questions/edit/{question_uid}",
        json={"answers": answers},
    )
    if response.status_code in [200, 422, 400]:
        typer.echo(pprint(response.json()))
    else:
        typer.echo(f"ERROR: {response.reason}")


def edit_question(client):
    # Retrieve current question
    current_status = question_details(client)
    if not current_status:
        return

    question_uid = current_status["uid"]

    text = input("Text:  ") or current_status["text"]
    position = input("Position:  ") or current_status["position"]
    boolean = input("Boolean:  ") or current_status["boolean"]
    time = input("Time:  ") or current_status["time"]

    payload = {"text": text, "position": position, "boolean": boolean, "time": time}

    typer.echo("Updating Question")
    response = client.put(f"{BASE_URL}/questions/edit/{question_uid}", json=payload)

    if response.status_code in [200, 422, 400]:
        typer.echo(pprint(response.json()))
    else:
        typer.echo(f"ERROR: {response.reason}")


def list_questions(client):
    match_uid = input("Match ID: ")
    match_uid = None if match_uid == "" else int(match_uid)
    response = client.get(f"{BASE_URL}/questions/", params={"match_uid": match_uid})
    if response.ok:
        for question in response.json()["questions"]:
            typer.echo(pprint(question))
    else:
        typer.echo(f"ERROR: {response.reason}")


def upload_yaml(client):

    if input("Create a new match?  ") == "y":
        new_match()

    # the file must reside anywhere under proquiz/backend/app/quizzes
    file_name = input("File name ==> ")
    match_uid = input("The Match UID ==> ")
    file_path = "/app/quizzes/" + file_name + ".yaml"
    with open(file_path, "rb") as fp:
        b64content = b64encode(fp.read()).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"

        payload = {"uid": match_uid, "data": b64string}
        result = client.post(f"{BASE_URL}/matches/yaml_import", json=payload)
        typer.echo((result.status_code, result.json()))


def play(client):
    response = client.get(f"{BASE_URL}/matches")
    typer.echo("List of Matches:\n")
    all_matches = {}
    for i, _match in enumerate(response.json()["matches"]):
        all_matches[i] = _match
        visibility = "restricted" if _match["is_restricted"] else "public"
        typer.echo(f"n. {i} :: {_match['name']} :: {visibility}")

    typer.echo("\n\n")
    match_number = input("Enter match number or q(quit): ")
    if match_number == "q":
        exit_command()

    name = all_matches[int(match_number)]["name"]
    typer.echo(f"Playing...at {name}")

    if all_matches[int(match_number)]["is_restricted"]:
        match_password = input("Insert password for the match: ")
    else:
        match_password = None

    # create a new client with new headers (i.e. unauthenticated)
    client = Client()

    sign_in = input("Do you want to sign-in (y/n) ? ")
    user_uid = None
    if sign_in == "y":
        user_uid = player_sign(None)

    if all_matches[int(match_number)]["uhash"]:
        uhash = all_matches[int(match_number)]["uhash"]
        response = client.post(f"{BASE_URL}/play/h/{uhash}")
    else:
        code = all_matches[int(match_number)]["code"]
        response = client.post(f"{BASE_URL}/play/code", json={"match_code": code})

    if response.status_code in [200, 422, 400]:
        typer.echo(pprint(response.json()))

    if not response.ok:
        typer.echo(response.reason)
        return

    payload = {"match_uid": response.json()["match_uid"]}
    if user_uid:
        payload.update(user_uid=user_uid)
    if match_password:
        payload.update(password=match_password)

    response = client.post(f"{BASE_URL}/play/start", json=payload)
    if response.status_code in [422, 400]:
        typer.echo(pprint(response.json()))

    if not response.ok:
        typer.echo(response.reason)
        return

    response_data = response.json()
    current_game_id = response_data["question"]["game"]["uid"]
    while response_data["question"] is not None:
        if response_data["question"]["game"]["uid"] != current_game_id:
            current_game_id = response_data["question"]["game"]["uid"]
            index = response_data["question"]["game"]["index"]
            typer.echo(f"Starting {index} Game")
            sleep(1)

        answer_map = print_question_and_answers(response_data["question"])
        open_answer_text = None
        answer_uid = None
        if not answer_map:
            open_answer_text = input("Answer: ")
        else:
            question_time = response_data["question"]["time"]
            if question_time:
                typer.echo(f"You have {question_time} seconds to answer!")

            index, o, e = select.select([sys.stdin], [], [], question_time)

            if index:
                index = sys.stdin.readline().strip()
                if int(index[0]) not in answer_map:
                    index = 0
                answer_uid = answer_map[int(index)]
            else:
                typer.echo("No answer!")
                answer_uid = None

        response = client.post(
            f"{BASE_URL}/play/next",
            json={
                "match_uid": response_data["match_uid"],
                "question_uid": response_data["question"]["uid"],
                "answer_uid": answer_uid,
                "answer_text": open_answer_text,
                "user_uid": response_data["user_uid"],
            },
        )
        response_data = response.json()
        if response.status_code in [422, 400]:
            typer.echo(pprint(response.json()))
            return

    typer.echo("\n\n")
    typer.echo(f"Match Over. Your score is: {response_data['score']}")


def print_question_and_answers(question):
    answer_map = {}
    typer.echo(f"{question['text']}\n")
    for i, answer in enumerate(question["answers_to_display"]):
        typer.echo(f"{i}:\t{answer['text']}")
        answer_map[i] = answer["uid"]

    typer.echo("\n\n")
    return answer_map


def list_all_players(client):
    match_uid = input("Match ID: ")
    if not match_uid:
        signed = input("Signed y/n: ") == "y"
        response = client.get(f"{BASE_URL}/players", params={"signed": signed})
    else:
        response = client.get(f"{BASE_URL}/players/{match_uid}")

    if response.status_code in [422, 400]:
        typer.echo(pprint(response.json()))
    else:
        typer.echo(response.reason)

    for user in response.json()["players"]:
        typer.echo(pprint(user))


def player_sign(_):
    original_email = input("Original email: ")
    token = input("Token (birthday ddmmyyyy): ")
    if not (original_email or token):
        return

    client = Client()
    response = client.post(
        f"{BASE_URL}/play/sign", json={"email": original_email, "token": token}
    )
    if response.status_code in [200, 422, 400]:
        typer.echo(pprint(response.json()))
        return response.json()["user"]
    else:
        typer.echo(response.reason)


def create_new_signed_user(_):
    original_email = input("Original email: ")
    token = input("Token (birthday ddmmyyyy): ")
    if not (original_email or token):
        return

    client = Client()
    response = client.post(
        f"{BASE_URL}/players/sign", json={"email": original_email, "token": token}
    )
    if response.status_code in [200, 422, 400]:
        typer.echo(pprint(response.json()))
    else:
        typer.echo(response.reason)


def get_ranking_for_a_match(_):
    match_uid = input("Enter the match ID:  ")
    client = Client()
    response = client.get(f"{BASE_URL}/matches/rankings/{match_uid}")
    if not response.ok:
        typer.echo(response.reason)
        return

    typer.echo("\n\n")
    for rank in response.json()["rankings"]:
        username = rank["user"]["name"] or "no-name"
        typer.echo(f"User {username} ({rank['user']['uid']}): {rank['score']}")


def import_questions_to_match(client):
    typer.echo("Work in progress")
    if client:
        return

    response = client.post(f"{BASE_URL}/matches/import_questions")
    if response.status_code in [200, 422, 400]:
        typer.echo(pprint(response.json()))
    else:
        typer.echo(response.reason)


def countdown(question_time):
    for sec in range(question_time):
        sys.stdout.write("\r")
        value = question_time - sec
        sys.stdout.flush()
        sys.stdout.write("%d seconds left" % value)
        sleep(1)


def exit_command():
    typer.echo("Exiting")
    sys.exit(0)


def menu():
    main_message = """
Choose your option:

    1. list matches
    2. get match details
    3. create a new match
    4. edit one match
    5. import questions with answers from YAML file to a match
    6. play
    7. create new question
    8. edit question
    9. list all questions
    10: list all players
    11: create new signed user
    12: player sign-in
    13: rankings of a match
    14. import question to a match
    15: edit_answers_of_question
    [enter] to exit
    """
    typer.echo(main_message)
    return input()


@app.command()
def start():
    client = Client()
    client.authenticate()

    while True:
        if input("\n\n[enter] for Menu, q/Q to exit: ") in ["q", "Q"]:
            exit_command()

        user_choice = menu()
        action = {
            "1": list_matches,
            "2": match_details,
            "3": new_match,
            "4": edit_match,
            "5": upload_yaml,
            "6": play,
            "7": new_question,
            "8": edit_question,
            "9": list_questions,
            "10": list_all_players,
            "11": create_new_signed_user,
            "12": player_sign,
            "13": get_ranking_for_a_match,
            "14": import_questions_to_match,
            "15": edit_answers_of_question,
        }.get(user_choice)
        if not action:
            exit_command()

        action(client)


if __name__ == "__main__":
    app()
