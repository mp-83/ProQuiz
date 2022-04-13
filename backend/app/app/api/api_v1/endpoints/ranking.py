import logging
from app.entities import Rankings
from app.core.security import login_required
from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter()


@login_required
@router.get("")
def match_rankings(self, user_input):
    match_uid = user_input["match_uid"]
    rankings = Rankings.of_match(match_uid)
    return {"rankings": [rank.json for rank in rankings]}
