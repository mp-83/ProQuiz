# from app.domain_entities import User
# from fastapi import status
# from fastapi.testclient import TestClient
#
# from app.core.config import settings


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

#
# class TestCaseLogin:
#     def t_failedLoginAttempt(self, client: TestClient, superuser_token_headers: dict, dbsession):
#         response = client.post(
#             f"{settings.API_V1_STR}/login",
#             json={"email": "user@test.com", "password": "psser"},
#             headers=superuser_token_headers,
#         )
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#
#     def t_successfulLogin(self, client: TestClient, superuser_token_headers: dict, dbsession):
#         credentials = {
#             "email": "user@test.com",
#             "password": "p@ssworth",
#         }
#         User(**credentials).save()
#         response = client.post(
#             f"{settings.API_V1_STR}/login",
#             json=credentials,
#             headers=superuser_token_headers,
#         )
#         assert response.status_code == status.HTTP_303_SEE_OTHER
#
#
# class TestCaseLogOut:
#     def t_cookiesAfterLogoutCompletedSuccessfully(self, client: TestClient, superuser_token_headers: dict, dbsession):
#         response = client.post(
#             f"{settings.API_V1_STR}/login",
#             headers=superuser_token_headers,
#         )
#         assert response.status_code == status.HTTP_303_SEE_OTHER
#         assert "Set-Cookie" in dict(response.headers)
#
#     def t_usingGetInsteadOfPostWhenCallingLogout(self, client: TestClient, dbsession):
#         response = client.get(f"{settings.API_V1_STR}/login")
#         assert response.status_code == status.HTTP_303_SEE_OTHER
#         assert "Set-Cookie" not in dict(response.headers)
