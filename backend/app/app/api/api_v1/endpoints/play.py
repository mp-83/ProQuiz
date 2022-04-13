import logging

from app import schemas
from app.entities.user import UserFactory
from app.exceptions import MatchOver, NotFoundObjectError, ValidateError
from app.play.single_player import PlayerStatus, PlayScore, SinglePlayer
from app.validation.logical import (
    ValidatePlayCode,
    ValidatePlayLand,
    ValidatePlayNext,
    ValidatePlaySign,
    ValidatePlayStart,
)
from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{match_uhash}")
def land(match_uhash: str):
    # TODO land_play_schema
    try:
        data = ValidatePlayLand(**{"match_uhash": match_uhash}).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return Response(status_code=status.HTTP_400_BAD_REQUEST, json={"error": e.message})

    match = data.get("match")
    return Response(json={"match": match.uid})


@router.post("/code")
def code(user_input):
    # TODO code_play_schema
    try:
        data = ValidatePlayCode(**user_input).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status=404)
        return Response(status=400, json={"error": e.message})

    match = data.get("match")
    user = UserFactory(signed=True).fetch()
    return Response(json={"match": match.uid, "user": user.uid})


@router.post("/start")
def start(user_input):
    # TODO start_play_schema
    try:
        data = ValidatePlayStart(**user_input).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status=404)
        return Response(status=400, json={"error": e.message})

    match = data.get("match")
    user = data.get("user")
    if not user:
        user = UserFactory(signed=match.is_restricted).fetch()

    status = PlayerStatus(user, match)
    player = SinglePlayer(status, user, match)
    current_question = player.start()
    match_data = {
        "match": match.uid,
        "question": current_question.json,
        "user": user.uid,
    }
    return Response(json=match_data)


@router.post("/next")
def next(user_input):
    # TODO next_play_schema
    try:
        data = ValidatePlayNext(**user_input).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status=404)
        return Response(status=400, json={"error": e.message})

    match = data.get("match")
    user = data.get("user")
    answer = data.get("answer")

    status = PlayerStatus(user, match)
    player = SinglePlayer(status, user, match)
    try:
        next_q = player.react(answer)
    except MatchOver:
        PlayScore(match.uid, user.uid, status.current_score()).save_to_ranking()
        return Response(json={"question": None})

    return Response(json={"question": next_q.json, "user": user.uid})


@router.post("/sign")
def sign(user_input):
    # TODO sign_play_schema
    try:
        data = ValidatePlaySign(**user_input).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status=404)
        return Response(status=400, json={"error": e.message})

    user = data.get("user")
    return Response(json={"user": user.uid})
