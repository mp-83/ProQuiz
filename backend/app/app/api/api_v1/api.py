from fastapi import APIRouter

from app.api.api_v1.endpoints import login, match, play, question, user

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(match.router, prefix="/matches", tags=["matches"])
api_router.include_router(question.router, prefix="/questions", tags=["questions"])
api_router.include_router(play.router, prefix="/play", tags=["play"])
api_router.include_router(user.router, prefix="/players", tags=["players"])
