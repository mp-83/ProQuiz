import pytest

from app.domain_service.data_transfer.user import UserDTO


class TestCaseUserFactory:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.user_dto = UserDTO(session=db_session)

    def test_fetchNewSignedUser(self, monkeypatch):
        monkeypatch.setenv(
            "SIGNED_KEY", "3ba57f9a004e42918eee6f73326aa89d", prepend=None
        )
        signed_user = self.user_dto.fetch(original_email="test@progame.io")
        assert signed_user.email == "916a55cf753a5c847b861df2bdbbd8de@progame.io"
        assert signed_user.email_digest == "916a55cf753a5c847b861df2bdbbd8de"

    def test_fetchExistingSignedUser(self, monkeypatch):
        monkeypatch.setenv(
            "SIGNED_KEY", "3ba57f9a004e42918eee6f73326aa89d", prepend=None
        )
        signed_user = self.user_dto.new(
            email_digest="916a55cf753a5c847b861df2bdbbd8de",
            token_digest="2357e975e4daaee0348474750b792660",
        )
        self.user_dto.save(signed_user)
        assert signed_user is not None
        assert (
            self.user_dto.fetch(original_email="test@progame.io", token="25111961")
            == signed_user
        )

    def test_fetchUnsignedUserShouldReturnNewUserEveryTime(self, mocker):
        # called twice to showcase the expected behaviour
        mocker.patch(
            "app.domain_service.data_transfer.user.uuid4",
            return_value=mocker.Mock(hex="3ba57f9a004e42918eee6f73326aa89d"),
        )
        unsigned_user = self.user_dto.fetch()
        assert unsigned_user.email == "uns-3ba57f9a004e42918eee6f73326aa89d@progame.io"
        assert not unsigned_user.token_digest
        mocker.patch(
            "app.domain_service.data_transfer.user.uuid4",
            return_value=mocker.Mock(hex="eee84145094cc69e4f816fd9f435e6b3"),
        )
        unsigned_user = self.user_dto.fetch()
        assert unsigned_user.email == "uns-eee84145094cc69e4f816fd9f435e6b3@progame.io"
        assert not unsigned_user.token_digest

    def test_fetchSignedUserWithoutOriginalEmailCreatesNewUser(self, monkeypatch):
        monkeypatch.setenv(
            "SIGNED_KEY", "3ba57f9a004e42918eee6f73326aa89d", prepend=None
        )
        signed_user = self.user_dto.fetch(signed=True)
        another_user = self.user_dto.fetch(signed=True)
        assert signed_user.email != another_user.email

    def test_createNewInternalUser(self):
        internal_user = self.user_dto.fetch(
            email="user@test.project", password="password"
        )
        assert internal_user.email == "user@test.project"
        assert internal_user.check_password("password")
        assert internal_user.create_timestamp is not None

    def test_fetchExistingInternalUser(self):
        new_internal_user = self.user_dto.fetch(
            email="internal@progame.io", password="password"
        )
        existing_user = self.user_dto.fetch(email=new_internal_user.email)
        assert existing_user == new_internal_user
