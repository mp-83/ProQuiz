from fastapi import status
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import settings
from app.domain_service.data_transfer.user import UserDTO

#
# class TestCaseLoginRequired:
#     # TODO: check why this test should stay as it is
#     def t_checkDefaultEndPointsAreDecorated(self, dummy_request, config):
#         protected_endpoints = (
#             (QuestionEndPoints, "new_question"),
#             (QuestionEndPoints, "get_question"),
#             (QuestionEndPoints, "edit_question"),
#             (MatchEndPoints, "create_match"),
#             (MatchEndPoints, "edit_match"),
#             (MatchEndPoints, "get_match"),
#             (MatchEndPoints, "list_matches"),
#         )
#         for endpoint_cls, endpoint_name in protected_endpoints:
#             endpoint_obj = endpoint_cls(dummy_request)
#             endpoint_method = getattr(endpoint_obj, endpoint_name)
#             response = endpoint_method()
#             assert isinstance(response, HTTPSeeOther)


class TestCaseLogin:
    def t_failedLoginAttempt(
        self, client: TestClient, superuser_token_headers: dict, db_session
    ):
        response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": "user@test.com", "password": "psser"},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def t_successfulLogin(
        self, client: TestClient, superuser_token_headers: dict, db_session
    ):
        dto = UserDTO(session=db_session)
        new_user = dto.new(email="user@test.com", password="p@ssworth")
        dto.save(new_user)
        response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": "user@test.com", "password": "psser"},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["access_token"]

    def t_tokenCorrectness(self, client: TestClient, access_token_expires, db_session):
        dto = UserDTO(session=db_session)
        new_user = dto.new(email="user@test.com", password="p@ssworth")
        dto.save(new_user)
        token = security.create_access_token(
            new_user.uid, expires_delta=access_token_expires
        )
        response = client.post(
            f"{settings.API_V1_STR}/login/test-token",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.ok
        assert response.json()["email"] == new_user.email


# class TestCaseLogOut:
#     def t_cookiesAfterLogoutCompletedSuccessfully(self, client: TestClient, superuser_token_headers: dict, db_session):
#         response = client.post(
#             f"{settings.API_V1_STR}/logout",
#             headers=superuser_token_headers,
#         )
#         assert response.status_code == status.HTTP_303_SEE_OTHER
#         assert "Set-Cookie" in dict(response.headers)
