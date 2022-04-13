import logging

from app.entities import Users
from app.core.security import login_required
from app.validation.syntax import player_list_schema
from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter()


@login_required
@router.get("/players")
def list_players(user_input):
    match_uid = user_input["match_uid"]
    all_players = Users.players_of_match(match_uid)
    return Response(json={"players": [u.json for u in all_players]})
