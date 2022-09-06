from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.constants import OPEN_ANSWER_TEXT_MAX_LENGTH, URL_LENGTH
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import QAppenderClass, TableMixin


class OpenAnswer(TableMixin, Base):
    __tablename__ = "open_answers"

    text = Column(String(OPEN_ANSWER_TEXT_MAX_LENGTH), nullable=False)
    content_url = Column(String(URL_LENGTH))
    reactions = relationship(
        "Reaction",
        viewonly=True,
        order_by="Reaction.uid",
        lazy="dynamic",
        query_class=QAppenderClass,
    )

    @property
    def level(self):
        return
