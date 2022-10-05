import logging
import os
from random import randint
from time import sleep

from locust import HttpUser, between, task
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


BASE_URL = "http://backend:7070/api/v1"


class BackEndApi(HttpUser):
    wait_time = between(3, 5)

    def __init__(self, *args, **kwargs):
        super(BackEndApi, self).__init__(*args, **kwargs)
        self.restricted_matches = []
        self.public_matches = []

    def on_start(self):
        username = os.getenv("FIRST_SUPERUSER")
        password = os.getenv("FIRST_SUPERUSER_PASSWORD")

        response = self.client.post(
            f"{BASE_URL}/login/access-token",
            data={"username": username, "password": password},
        )
        if not response.ok:
            logger.debug(f"{response.status_code} - {response.reason}")
        token = response.json().get("access_token")
        self.client.headers.update(**{"Authorization": f"Bearer {token}"})
        matches = self.list_matches()
        self.restricted_matches = [
            (match["uid"], match["uhash"], match["password"])
            for match in matches
            if match["is_restricted"]
        ]
        self.public_matches = [
            (match["uid"], match["uhash"], match["code"])
            for match in matches
            if not match["is_restricted"]
        ]
        self.client.headers.pop("Authorization", None)

    def list_matches(self):
        response = self.client.get(f"{BASE_URL}/matches/")
        if not response.ok:
            return {}
        return response.json()["matches"]

    def player_sign(self):
        users = [
            ("rob@aol.com", "20081990"),
            ("alixa@gm.com", "05031950"),
            ("greg@yahoo.com", "28041980"),
            ("ross@gl.com", "11052001"),
            ("paul@mail.com", "30091995"),
        ]
        idx = randint(0, len(users) - 1)
        email, token = users[idx]

        response = self.client.post(
            f"{BASE_URL}/play/sign", json={"email": email, "token": token}
        )
        if response.ok:
            logger.info(f"Logged in: {email}")
            return response.json()["user"]
        else:
            logger.error(f"{response.status_code}: {email}")

    @task
    def play_restricted_matches(self):
        n = randint(0, len(self.restricted_matches) - 1)
        match_uid, match_uhash, password = self.restricted_matches[n]
        response = self.client.post(f"{BASE_URL}/play/h/{match_uhash}")

        if response.ok:
            logger.info(response.json())
        elif response.status_code in [422, 400]:
            logger.error(response.json())
            return

        payload = {"match_uid": response.json()["match_uid"]}
        # user_uid = self.player_sign()
        # if not user_uid:
        #     self.client.headers.pop("Authorization", None)
        #     return

        # payload.update(user_uid=user_uid)
        if password:
            payload["password"] = password

        logger.info(f"Starting match {match_uhash}: {payload}")
        response = self.client.post(f"{BASE_URL}/play/start", json=payload)
        if not response.ok:
            logger.error(f"{response.status_code}: {payload}")
            return

        response_data = response.json()
        current_game_id = response_data["question"]["game"]["uid"]
        while response_data["question"] is not None:
            question = response_data["question"]
            if question["game"]["uid"] != current_game_id:
                current_game_id = question["game"]["uid"]
                index = question["game"]["index"]
                logger.info(f"Starting Game {index} of match {match_uid}")

            question_time = response_data["question"]["time"] or 11
            time_upper_bound = min(question_time, 10)
            wait_seconds = randint(3, time_upper_bound)
            sleep(wait_seconds)

            answer_idx = randint(0, len(question["answers_to_display"]) - 1)
            answer = question["answers_to_display"][answer_idx]

            payload = {
                "match_uid": response_data["match_uid"],
                "question_uid": response_data["question"]["uid"],
                "answer_uid": answer["uid"],
                "user_uid": response_data["user_uid"],
            }

            response = self.client.post(f"{BASE_URL}/play/next", json=payload)
            try:
                response_data = response.json()
            except RequestException:
                logger.error(f"{response.status_code}: {match_uhash} - {payload}")
                break

        logger.info(f"Completed restricted match {match_uhash}")
        self.client.headers.pop("Authorization", None)

    @task
    def play_public_match(self):
        n = randint(0, len(self.public_matches) - 1)
        match_uid, match_uhash, match_code = self.public_matches[n]

        if match_uhash:
            response = self.client.post(f"{BASE_URL}/play/h/{match_uhash}")
        else:
            response = self.client.post(
                f"{BASE_URL}/play/code", json={"match_code": match_code}
            )

        if response.ok:
            logger.info(response.json())
        elif response.status_code in [422, 400]:
            logger.error(response.json())
            return

        payload = {"match_uid": response.json()["match_uid"]}
        logger.info(f"Starting match {match_uhash or match_code}: {payload}")
        response = self.client.post(f"{BASE_URL}/play/start", json=payload)
        if not response.ok:
            logger.error(response.reason)
            return

        response_data = response.json()
        current_game_id = response_data["question"]["game"]["uid"]

        while response_data["question"] is not None:
            question = response_data["question"]
            if question["game"]["uid"] != current_game_id:
                current_game_id = question["game"]["uid"]
                index = question["game"]["index"]
                # TODO log.msg: starting game 1 of X
                logger.info(f"Starting Game {index} of match {match_uid}")

            question_time = response_data["question"]["time"] or 11
            time_upper_bound = min(question_time, 10)
            wait_seconds = randint(3, time_upper_bound)
            sleep(wait_seconds)

            answer_idx = randint(0, len(question["answers_to_display"]) - 1)
            answer = question["answers_to_display"][answer_idx]

            payload = {
                "match_uid": response_data["match_uid"],
                "question_uid": response_data["question"]["uid"],
                "answer_uid": answer["uid"],
                "user_uid": response_data["user_uid"],
            }

            response = self.client.post(f"{BASE_URL}/play/next", json=payload)
            try:
                response_data = response.json()
            except RequestException:
                logger.error(f"{response.status_code}: {match_uhash} - {payload}")
                break

        logger.info(f"Completed match {match_uhash or match_code}")
