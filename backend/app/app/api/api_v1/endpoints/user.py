import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.domain_entities import Users
from app.domain_entities.db.session import get_db
from app.validation import schemas

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{match_uid}", response_model=schemas.Players)
def list_players(match_uid: int, session: Session = Depends(get_db)):
    all_players = Users(db_session=session).players_of_match(match_uid)
    return {"players": all_players}
