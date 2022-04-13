import os

from redis import Redis


class ClientFactory:
    _client = None

    def new_client(self):
        if self._client is None:
            self._client = Redis(
                **{"host": "redis", "port": "6379", "password": os.getenv("REDIS_PW")}
            )
        return self._client
