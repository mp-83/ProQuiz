class TestCaseUserFactory:
    def test_1(self, monkeypatch, user_dto):
        """create new signed user via fetch"""
        monkeypatch.setenv(
            "SIGNED_KEY", "3ba57f9a004e42918eee6f73326aa89d", prepend=None
        )
        signed_user = user_dto.fetch(original_email="test@progame.io")
        assert signed_user.email == "916a55cf753a5c847b861df2bdbbd8de@progame.io"
        assert signed_user.email_digest == "916a55cf753a5c847b861df2bdbbd8de"

    def test_2(self, monkeypatch, user_dto):
        """
        GIVEN: an existing signed user
        WHEN: user_dto.fetch() is called with the email and token
        THEN: the existing user is returned
        """
        monkeypatch.setenv(
            "SIGNED_KEY", "3ba57f9a004e42918eee6f73326aa89d", prepend=None
        )
        signed_user = user_dto.new(
            email_digest="916a55cf753a5c847b861df2bdbbd8de",
            token_digest="2357e975e4daaee0348474750b792660",
        )
        user_dto.save(signed_user)
        assert signed_user is not None
        assert (
            user_dto.fetch(original_email="test@progame.io", token="25111961")
            == signed_user
        )

    def test_3(self, mocker, user_dto):
        """
        GIVEN: no existing users
        WHEN: fetch() is called twice without passing original-email
        THEN: two new unsigned users are returned
        """
        mocker.patch(
            "app.domain_service.data_transfer.user.uuid4",
            return_value=mocker.Mock(hex="3ba57f9a004e42918eee6f73326aa89d"),
        )
        unsigned_user = user_dto.fetch()
        assert unsigned_user.email == "uns-3ba57f9a004e42918eee6f73326aa89d@progame.io"
        assert not unsigned_user.token_digest
        mocker.patch(
            "app.domain_service.data_transfer.user.uuid4",
            return_value=mocker.Mock(hex="eee84145094cc69e4f816fd9f435e6b3"),
        )
        unsigned_user = user_dto.fetch()
        assert unsigned_user.email == "uns-eee84145094cc69e4f816fd9f435e6b3@progame.io"
        assert not unsigned_user.token_digest

    def test_4(self, monkeypatch, user_dto):
        """
        GIVEN: no existing users
        WHEN: fetch() is called with signed=True, but no original-email
                is passed as parameter
        THEN: two new signed users are created each time
        """
        monkeypatch.setenv(
            "SIGNED_KEY", "3ba57f9a004e42918eee6f73326aa89d", prepend=None
        )
        signed_user = user_dto.fetch(signed=True)
        another_user = user_dto.fetch(signed=True)
        assert signed_user.email != another_user.email

    def test_5(self, user_dto):
        """Create a new internal user"""
        internal_user = user_dto.fetch(email="user@test.project", password="password")
        assert internal_user.email == "user@test.project"
        assert internal_user.check_password("password")
        assert internal_user.create_timestamp is not None

    def test_6(self, user_dto):
        """
        GIVEN: an existing internal-user
        WHEN: fetch() is called using the email parameter
        THEN: the internal-user is returned
        """
        new_internal_user = user_dto.fetch(
            email="internal@progame.io", password="password"
        )
        existing_user = user_dto.fetch(email=new_internal_user.email)
        assert existing_user == new_internal_user
