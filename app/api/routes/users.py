import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import UserCreate, UserOut, UserPage, UserUpdate
from app.db.deps import get_current_user_from_token, get_mysql_session, get_redis
from app.services import user_service


router = APIRouter(prefix="/users", tags=["users"])


class LoginPayload(BaseModel):
    token: str
    user: dict[str, Any]


class LogoutPayload(BaseModel):
    token: str


SessionDept =  Annotated[AsyncSession, Depends(get_mysql_session)]


@router.post("", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    session: SessionDept,
):
    return await user_service.create_user(session, payload)


@router.get("", response_model=UserPage)
async def list_users(
    session: SessionDept,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=1000)] = 10,
):
    return await user_service.list_users(session, page, size)


@router.get("/raw", response_model=UserPage)
async def list_users_raw(
    session: SessionDept,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    username: Annotated[str | None, Query()] = None,
    age_min: Annotated[int | None, Query(ge=0)] = None,
    age_max: Annotated[int | None, Query(ge=0)] = None,
):
    return await user_service.list_users_raw(
        session, page, size, username, age_min, age_max
    )


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    session: SessionDept,
):
    user = await user_service.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: SessionDept,
):
    user = await user_service.update_user(session, user_id, payload)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    _current_user: Annotated[dict, Depends(get_current_user_from_token)],
    session: SessionDept,
):  
    
    ok = await user_service.delete_user(session, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"deleted": True, "id": user_id}


@router.post("/login")
async def login(
    payload: LoginPayload,
    redis: Annotated[Redis, Depends(get_redis)],
):
    user_json = json.dumps(payload.user, ensure_ascii=False)
    await redis.set(f"login:token:{payload.token}", user_json)
    return {"token": payload.token, "stored": True}


@router.post("/logout")
async def logout(
    payload: LogoutPayload,
    redis: Annotated[Redis, Depends(get_redis)],
):
    await redis.delete(f"login:token:{payload.token}")
    return {"token": payload.token, "deleted": True}
