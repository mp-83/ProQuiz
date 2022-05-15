import os
from hashlib import blake2b
from uuid import uuid4

from sqlalchemy.orm import Session

from app.constants import DIGEST_SIZE
from app.domain_entities.user import User


class UserDTO:
    def __init__(self, session: Session):
        self._session = session
        self.klass = User

    def new(self, **kwargs):
        password = kwargs.pop("password", None)
        instance = self.klass(**kwargs)
        if password:
            instance.set_password(password)
        return instance

    def save(self, instance):
        self._session.add(instance)
        self._session.commit()
        return instance

    def count(self):
        return self._session.query(self.klass).count()

    def get(self, **filters):
        return self._session.query(self.klass).filter_by(**filters).one_or_none()

    def all(self):
        return self._session.query(self.klass).all()

    def fetch(self, **kwargs):
        original_email = kwargs.pop("original_email", "")
        signed = kwargs.pop("signed", None) or original_email
        email = kwargs.get("email")
        password = kwargs.get("password")
        token = kwargs.get("token", "")

        return UserFactory(
            original_email=original_email,
            signed=signed,
            email=email,
            password=password,
            token=token,
            db_session=self._session,
        ).fetch()


class WordDigest:
    def __init__(self, word):
        self.word = word

    def value(self):
        key = os.getenv("SIGNED_KEY").encode("utf-8")
        h = blake2b(key=key, digest_size=DIGEST_SIZE)
        h.update(self.word.encode("utf-8"))
        return h.hexdigest()


class UserFactory:
    def __init__(self, **kwargs):
        self.original_email = kwargs.pop("original_email", "")
        self.signed = kwargs.pop("signed", None) or self.original_email
        self._session = kwargs.pop("db_session", None)
        self.email = kwargs.get("email")
        self.password = kwargs.get("password")
        self.token = kwargs.get("token", "")

        self.user_dto = UserDTO(session=self._session)

    def existing_user(self, email_digest, token_digest):
        return self.user_dto.get(email_digest=email_digest, token_digest=token_digest)

    def internal_user(self):
        email_digest = WordDigest(self.email).value()

        _internal_user = self.user_dto.get(email=self.email)
        return _internal_user or self.user_dto.save(
            self.user_dto.new(
                email=self.email,
                email_digest=email_digest,
                password=self.password,
                db_session=self._session,
            )
        )

    def unsigned_user(self):
        email_digest = uuid4().hex
        email = f"uns-{email_digest}@progame.io"
        new_user = self.user_dto.new(email=email)
        return self.user_dto.save(new_user)

    def signed_user(self, email_digest, token_digest):
        user = self.user_dto.new()
        user.email = f"{email_digest}@progame.io"
        user.email_digest = email_digest
        user.token_digest = token_digest
        return self.user_dto.save(user)

    def fetch(self):
        if self.email:
            return self.internal_user()

        if not self.signed:
            return self.unsigned_user()

        email_digest = WordDigest(self.original_email).value()
        token_digest = WordDigest(self.token).value()
        if self.existing_user(email_digest, token_digest):
            return self.existing_user(email_digest, token_digest)

        return self.signed_user(email_digest, token_digest)
