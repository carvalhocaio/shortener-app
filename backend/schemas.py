from typing import Optional

from pydantic import BaseModel


class URLBase(BaseModel):
    target_url: str
    custom_key: Optional[str] = None


class URL(URLBase):
    is_active: bool
    clicks: int

    class Config:
        orm_mode = True


class URLInfo(BaseModel):
    target_url: str
    is_active: bool
    clicks: int
    url: str
    admin_url: str

    class Config:
        orm_mode = True
