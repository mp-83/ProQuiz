import logging

from app import schemas
from app.entities import Game, Match, Matches, Question
from app.exceptions import NotFoundObjectError, ValidateError
from app.core.security import login_required
from app.validation.logical import (
    RetrieveObject,
    ValidateEditMatch,
    ValidateMatchImport,
)
from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
def list_matches():
    # TODO: to fix the filtering parameters
    all_matches = Matches.all_matches(**{})
    return {"matches": [m.json for m in all_matches]}


@router.get("/{uid}", response_model=schemas.Match)
def get_match(uid: int, response: Response):
    try:
        match = RetrieveObject(uid=uid, otype="match").get()
    except NotFoundObjectError as e:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    return {"match": match.json}


@router.post("/new", response_model=schemas.Match)
def create_match(user_input: dict):
    # TODO convert create_match_schema to Pydantic.schema
    questions = user_input.pop("questions", [])
    new_match = Match(**user_input).save()
    new_game = Game(match_uid=new_match.uid).save()
    for position, question in enumerate(questions):
        new = Question(
            game_uid=new_game.uid, text=question["text"], position=position
        )
        new.create_with_answers(question.get("answers"))
    return {"match": new_match.json}


@login_required
@router.put("/edit/{uid}", response_model=schemas.Match)
def edit_match(uid: int, user_input, response: Response):
    # TODO convert edit_match_schema to Pydantic.schema
    try:
        match = ValidateEditMatch(uid).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return Response(status_code=status.HTTP_400_BAD_REQUEST, json={"error": e.message})

    match.update(**user_input)
    return {"match": match.json}


@login_required
@router.post("/yaml_import", response_model=schemas.Match)
def match_yaml_import(user_input, response: Response):
    # tODO convert user_input to match_yaml_import_schema
    match_uid = user_input.get("match_uid")

    try:
        match = ValidateMatchImport(match_uid).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return Response(status_code=status.HTTP_400_BAD_REQUEST, json={"error": e.message})

    match.insert_questions(user_input["data"]["questions"])
    return {"match": match.json}
