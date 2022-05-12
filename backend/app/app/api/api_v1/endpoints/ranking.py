import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.domain_entities import Rankings
from app.domain_entities.db.session import get_db
from app.validation import schemas

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{match_uid}", response_model=schemas.MatchRanking)
def match_rankings(match_uid: int, session: Session = Depends(get_db)):
    rankings = Rankings(db_session=session).of_match(match_uid)
    return {"rankings": rankings}
