from app.entities import User


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
    def t_failedLoginAttempt(self, testapp):
        testapp.post_json(
            "/login",
            {"email": "user@test.com", "password": "psser"},
            status=400,
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
        )

    def t_successfulLogin(self, testapp):
        credentials = {
            "email": "user@test.com",
            "password": "p@ssworth",
        }
        User(**credentials).save()
        testapp.post_json(
            "/login",
            credentials,
            status=303,
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
        )


class TestCaseLogOut:
    def t_cookiesAfterLogoutCompletedSuccessfully(self, testapp):
        response = testapp.post(
            "/logout",
            status=303,
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
        )
        assert "Set-Cookie" in dict(response.headers)

    def t_usingGetInsteadOfPostWhenCallingLogout(self, testapp):
        response = testapp.get("/logout", status=303)
        assert "Set-Cookie" not in dict(response.headers)
