from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, ConfigDict


class ClarifyResponse(BaseModel):
    type: Literal["clarify"] = "clarify"
    question: str


class SqlResponse(BaseModel):
    type: Literal["sql"] = "sql"
    query: str
    db_engine: str = "postgresql"


class BlockResponse(BaseModel):
    type: Literal["blocked"] = "blocked"
    reason: str


ChatResponse = Annotated[
    Union[ClarifyResponse, SqlResponse, BlockResponse], Field(discriminator="type")
]


class UserBase(BaseModel):
    username: str | None = None
    password: str | None = None
    age: int | None = None
    ext_json: dict | None = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    age: int | None = None
    ext_json: dict | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    create_time: datetime


class UserPage(BaseModel):
    total: int
    page: int
    size: int
    items: list[UserOut]
