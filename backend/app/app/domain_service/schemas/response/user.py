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
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

    class Config:
        orm_mode = True


class Players(BaseModel):
    players: List[Player]
