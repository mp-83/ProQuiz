from typing import Dict

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain_entities.user import User
from app.domain_service.data_transfer.user import UserDTO
from app.tests.utilities.utils import random_email, random_lower_string


def user_authentication_headers(
    *, client: TestClient, email: str, password: str
) -> Dict[str, str]:
    data = {"username": email, "password": password}

    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=data)
    response = r.json()
    auth_token = response["access_token"]
    return {"Authorization": f"Bearer {auth_token}"}


def create_random_user(session: Session) -> User:
    email = random_email()
    password = random_lower_string()
    dto = UserDTO(session=session)
    user_in = dto.new(username=email, email=email, password=password)
    return dto.save(user_in)


def authentication_token_from_email(
    *, client: TestClient, email: str, session: Session
) -> Dict[str, str]:
    """
    Return a valid token for the user with given email.

    If the user doesn't exist it is created first.
    """
    password = random_lower_string()
    dto = UserDTO(session=session)
    user = dto.get(email=email)
    if not user:
        user_in_create = dto.new(username=email, email=email, password=password)
        dto.save(user_in_create)
    else:
        user.set_password(password)
        dto.save(user)

    return user_authentication_headers(client=client, email=email, password=password)
