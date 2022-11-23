from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import security
from app.core.config import settings
from app.domain_entities import User
from app.domain_entities.db.session import get_db
from app.domain_service.data_transfer.user import UserDTO
from app.domain_service.schemas import response
from app.domain_service.schemas import syntax_validation as syntax

router = APIRouter()


@router.post("/login/access-token", response_model=response.Token)
def login_access_token(
    session: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = UserDTO(session=session).get(email=form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user"
        )
    elif not user.check_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.uid, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/login/test-token", response_model=syntax.UserBase)
def test_token(current_user: User = Depends(get_current_user)) -> Any:
    """
    Test access token
    """
    return current_user


@router.get("/csrftoken")
async def get_csrf_token(csrf_protect: CsrfProtect = Depends()):
    response = JSONResponse(status_code=200, content={"csrf_token": "cookie"})
    csrf_protect.set_csrf_cookie(response)
    return response
