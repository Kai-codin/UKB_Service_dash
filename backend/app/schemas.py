from pydantic import BaseModel
from typing import List, Optional


class EnvBase(BaseModel):
    key: str
    value: str


class EnvCreate(EnvBase):
    pass


class Env(EnvBase):
    id: int

    class Config:
        orm_mode = True


class SiteBase(BaseModel):
    name: str
    base_path: Optional[str] = None
    base_command: Optional[str] = None


class SiteCreate(SiteBase):
    pass


class Site(SiteBase):
    id: int
    class Config:
        orm_mode = True


class CommandBase(BaseModel):
    name: str
    command_template: str


class CommandCreate(CommandBase):
    site_id: Optional[int] = None
    envs: Optional[List[EnvCreate]] = None


class Command(CommandBase):
    id: int
    site_id: int
    envs: List[Env] = []

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    perms: Optional[str] = ""


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    perms: str

    class Config:
        orm_mode = True


class LoginData(BaseModel):
    username: str
    password: str
