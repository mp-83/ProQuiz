import logging

from fastapi import APIRouter, Depends, Request
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy.orm import Session

from app.domain_entities.db.session import get_db
from app.domain_service.data_transfer.user import UserDTO
from app.domain_service.schemas import response
from app.domain_service.schemas import syntax_validation as syntax

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{match_uid}", response_model=response.Players)
def list_players_of_match(match_uid: int, session: Session = Depends(get_db)):
    dto = UserDTO(session=session)
    all_players = dto.players_of_match(match_uid)
    return {"players": all_players}


@router.get("/", response_model=response.Players)
def players(signed: bool = None, session: Session = Depends(get_db)):
    dto = UserDTO(session=session)
    query_method = {
        True: dto.signed,
        False: dto.unsigned,
    }.get(signed, dto.all)
    all_players = query_method()
    return {"players": all_players}


@router.post("/sign", response_model=response.Player)
def register_signed_user(
    user_input: syntax.SignedUserCreate,
    request: Request,
    session: Session = Depends(get_db),
    csrf_protect: CsrfProtect = Depends(),
):
    csrf_protect.validate_csrf_in_cookies(request)
    user_input = user_input.dict()
    dto = UserDTO(session=session)
    return dto.fetch(original_email=user_input["email"], token=user_input["token"])
