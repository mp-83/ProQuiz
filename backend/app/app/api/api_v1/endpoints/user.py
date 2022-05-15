import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.domain_entities.db.session import get_db
from app.domain_service.data_transfer.user import UserDTO
from app.domain_service.validation import syntax

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{match_uid}", response_model=syntax.Players)
def list_players(match_uid: int, session: Session = Depends(get_db)):
    dto = UserDTO(session=session)
    all_players = dto.players_of_match(match_uid)
    return {"players": all_players}
