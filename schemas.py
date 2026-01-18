from typing import Literal, Union, Annotated

from pydantic import BaseModel, Field


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
