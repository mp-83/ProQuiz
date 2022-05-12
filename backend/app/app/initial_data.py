import logging

from app.domain_entities.db.init_db import init_db
from app.domain_entities.db.session import session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init() -> None:
    _session = session_factory()
    init_db(_session)


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
