import bcrypt
from sqlalchemy import Boolean, Column, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session

from app.constants import (
    DIGEST_LENGTH,
    EMAIL_MAX_LENGTH,
    KEY_LENGTH,
    PASSWORD_HASH_LENGTH,
    USER_NAME_MAX_LENGTH,
)
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


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
    def json(self):
        return {"uid": self.uid, "email": self.email, "name": self.name}
