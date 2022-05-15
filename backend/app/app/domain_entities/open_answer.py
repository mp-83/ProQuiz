from sqlalchemy import Column, String

from app.constants import OPEN_ANSWER_TEXT_MAX_LENGTH, URL_LENGTH
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


class OpenAnswer(TableMixin, Base):
    __tablename__ = "open_answers"

    text = Column(String(OPEN_ANSWER_TEXT_MAX_LENGTH), nullable=False)
    content_url = Column(String(URL_LENGTH))
    # reactions: implicit backward relation

    @property
    def level(self):
        return
