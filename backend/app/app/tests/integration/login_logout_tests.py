from fastapi import status
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import settings


class TestCaseLogin:
    def test_1(self, client: TestClient, db_session):
        """Failed login attempt"""
        response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": "user@test.com", "password": "psser"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_2(self, client: TestClient, superuser_token_headers: dict, user_dto):
        """Successful login"""
        new_user = user_dto.new(email="user@test.com", password="p@ssworth")
        user_dto.save(new_user)
        response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": "user@test.com", "password": "p@ssworth"},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["access_token"]

    def test_3(self, client: TestClient, access_token_expires, user_dto):
        """Verify the correctness of the token"""
        new_user = user_dto.new(email="user@test.com", password="p@ssworth")
        user_dto.save(new_user)
        token = security.create_access_token(
            new_user.uid, expires_delta=access_token_expires
        )
        response = client.post(
            f"{settings.API_V1_STR}/login/test-token",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.ok
        assert response.json()["email"] == new_user.email
