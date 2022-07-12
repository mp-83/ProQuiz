from typing import List, Optional

from pydantic import BaseModel, EmailStr


# Might be useful
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = None

    class Config:
        orm_mode = True


class Player(BaseModel):
    uid: int
    signed: bool
    email: str
    full_name: Optional[str] = ""
    is_active: Optional[bool] = True

    class Config:
        orm_mode = True


class Players(BaseModel):
    players: List[Player]
