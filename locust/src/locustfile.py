import logging
import os

from locust import HttpUser, between, task

logger = logging.getLogger(__name__)


BASE_URL = "http://backend:7070/api/v1"


class BackEndApi(HttpUser):
    wait_time = between(3, 5)

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

    @task
    def list_matches(self):
        response = self.client.get(f"{BASE_URL}/matches/")
        if not response.ok:
            return
        logging.debug(response.json())
