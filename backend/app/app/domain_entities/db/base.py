# Import all the models, so that Base has them before being
# imported by Alembic
from app.domain_entities.db.base_class import Base  # noqa
