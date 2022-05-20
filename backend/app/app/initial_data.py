import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain_entities.db.session import session_factory
from app.domain_service.data_transfer.user import UserDTO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# make sure all SQL Alchemy models are imported (app.db.base) before initializing DB
# otherwise, SQL Alchemy might fail to initialize relationships properly
# for more details: https://github.com/tiangolo/full-stack-fastapi-postgresql/issues/28
def populate_database(db: Session) -> None:
    dto = UserDTO(session=db)
    user = dto.get(email=settings.FIRST_SUPERUSER)
    if not user:
        logger.info(f"Creating {settings.FIRST_SUPERUSER}")
        user_in = dto.new(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_admin=True,
        )
        user = dto.save(user_in)  # noqa: F841


def main() -> None:
    logger.info("Creating initial data")

    _session = session_factory()
    populate_database(_session)

    logger.info("Database is now populated")


if __name__ == "__main__":
    main()
