import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.domain_entities.db.session import get_db
from app.domain_service.data_transfer.ranking import RankingDTO
from app.domain_service.schemas import syntax_validation as syntax

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{match_uid}", response_model=syntax.MatchRanking)
def match_rankings(match_uid: int, session: Session = Depends(get_db)):
    rankings = RankingDTO(session=session).of_match(match_uid)
    return {"rankings": rankings}
