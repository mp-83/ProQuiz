from sqlalchemy.orm import Session

from app.domain_entities.answer import Answer


class AnswerDTO:
    def __init__(self, session: Session):
        self._session = session
        self.klass = Answer

    def new(self, **kwargs):
        """
        Instantiate a new object

        Cast the boolean value to text.
        """
        text = kwargs.get("text")
        kwargs["text"] = {False: "False", True: "True"}.get(text, text)

        kwargs.pop("uid", None)
        return self.klass(**kwargs)

    def save(self, instance):
        self._session.add(instance)
        self._session.commit()

    def count(self):
        return self._session.query(self.klass).count()

    def get(self, **filters):
        return self._session.query(self.klass).filter_by(**filters).one_or_none()

    def nullable_column(self, name):
        return self.klass.__table__.columns.get(name).nullable

    def update(self, instance, **kwargs):
        commit = kwargs.pop("commit", False)
        kwargs.pop("uid", None)
        for k, v in kwargs.items():
            if not hasattr(instance, k) or (v is None and not self.nullable_column(k)):
                continue
            setattr(instance, k, v)

        if commit:
            self._session.commit()
