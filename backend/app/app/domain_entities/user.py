import os
from hashlib import blake2b
from uuid import uuid4

import bcrypt
from sqlalchemy import Boolean, Column, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session

from app.constants import (
    DIGEST_LENGTH,
    DIGEST_SIZE,
    EMAIL_MAX_LENGTH,
    KEY_LENGTH,
    PASSWORD_HASH_LENGTH,
    USER_NAME_MAX_LENGTH,
)
from app.domain_entities import Reaction
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


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
        self.kwargs = kwargs

    def exists(self, email_digest, token_digest):
        return Users(db_session=self._session).get(
            email_digest=email_digest, token_digest=token_digest
        )

    def fetch(self):
        email = self.kwargs.get("email")
        if email:
            email_digest = WordDigest(email).value()
            password = self.kwargs.get("password")

            internal_user = Users(db_session=self._session).get(email=email)
            return (
                internal_user
                or User(
                    email=email,
                    email_digest=email_digest,
                    password=password,
                    db_session=self._session,
                ).save()
            )

        if not self.signed:
            email_digest = uuid4().hex
            email = f"uns-{email_digest}@progame.io"
            return User(email=email, db_session=self._session).save()

        token = self.kwargs.get("token", "")
        email_digest = WordDigest(self.original_email).value()
        token_digest = WordDigest(token).value()
        user = self.exists(email_digest, token_digest)
        if user:
            return user

        user = User(db_session=self._session)
        user.email = f"{email_digest}@progame.io"
        user.email_digest = email_digest
        user.token_digest = token_digest
        user.save()
        return user


class User(TableMixin, Base):
    __tablename__ = "users"

    email = Column(String(EMAIL_MAX_LENGTH), unique=True)
    email_digest = Column(String(DIGEST_LENGTH))
    token_digest = Column(String(DIGEST_LENGTH))
    name = Column(String(USER_NAME_MAX_LENGTH))
    password_hash = Column(String(PASSWORD_HASH_LENGTH))
    # reactions: implicit backward relation
    # user_rankings: implicit backward relation
    key = Column(String(KEY_LENGTH))
    is_admin = Column(Boolean, default=False)

    def __init__(self, db_session: Session = None, **kwargs):
        self._session = db_session
        password = kwargs.pop("password", None)
        if password:
            self.set_password(password)

        super().__init__(**kwargs)

    @hybrid_property
    def signed(self):
        return self.email_digest is not None

    def set_password(self, pw):
        pwhash = bcrypt.hashpw(pw.encode("utf8"), bcrypt.gensalt())
        self.password_hash = pwhash.decode("utf8")

    def check_password(self, pw):
        if self.password_hash is not None:
            expected_hash = self.password_hash.encode("utf8")
            return bcrypt.checkpw(pw.encode("utf8"), expected_hash)
        return False

    @property
    def session(self):
        return self._session

    def save(self):
        self.session.add(self)
        self.session.commit()
        return self

    @property
    def json(self):
        return {"uid": self.uid, "email": self.email, "name": self.name}


class Users:
    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def count(self):
        return self._session.query(User).count()

    def get(self, **filters):
        return self._session.query(User).filter_by(**filters).one_or_none()

    def all(self):
        return self._session.query(User).all()

    def players_of_match(self, match_uid):
        return (
            self._session.query(User)
            .join(Reaction, Reaction.user_uid == User.uid)
            .filter(Reaction.match_uid == match_uid)
            .all()
        )
