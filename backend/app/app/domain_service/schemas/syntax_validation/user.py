from typing import List, Optional

from pydantic import BaseModel, EmailStr

from app.domain_service.schemas.syntax_validation.play import SignPlay


# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = None

    class Config:
        orm_mode = True


class Player(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

    class Config:
        orm_mode = True


class Players(BaseModel):
    players: List[Player]


# Properties to receive via API on creation
class SignedUserCreate(SignPlay):
    """"""


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None


class User(BaseModel):
    email: EmailStr
    email_digest: Optional[str] = None
    token_digest: Optional[str] = None
    name: str = None
    password_hash: str = None
    key: str = None
    is_admin: bool = False
