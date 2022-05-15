from typing import Dict

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import domain_service
from app.core.config import settings
from app.domain_entities.user import User
from app.domain_service.validation.syntax import UserCreate, UserUpdate
from app.tests.utilities.utils import random_email, random_lower_string


def user_authentication_headers(
    *, client: TestClient, email: str, password: str
) -> Dict[str, str]:
    data = {"username": email, "password": password}

    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=data)
    response = r.json()
    auth_token = response["access_token"]
    return {"Authorization": f"Bearer {auth_token}"}


def create_random_user(db: Session) -> User:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(username=email, email=email, password=password)
    return domain_service.user.create(db=db, obj_in=user_in)


def authentication_token_from_email(
    *, client: TestClient, email: str, db: Session
) -> Dict[str, str]:
    """
    Return a valid token for the user with given email.

    If the user doesn't exist it is created first.
    """
    password = random_lower_string()
    user = domain_service.user.get_by_email(db, email=email)
    if not user:
        user_in_create = UserCreate(username=email, email=email, password=password)
        domain_service.user.create(db, obj_in=user_in_create)
    else:
        user_in_update = UserUpdate(password=password)
        domain_service.user.update(db, db_obj=user, obj_in=user_in_update)

    return user_authentication_headers(client=client, email=email, password=password)