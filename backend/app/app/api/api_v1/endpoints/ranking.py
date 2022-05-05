import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.db.session import get_db
from app.entities import Rankings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{match_uid}", response_model=schemas.MatchRanking)
def match_rankings(match_uid: int, session: Session = Depends(get_db)):
    rankings = Rankings(db_session=session).of_match(match_uid)
    return {"rankings": rankings}
