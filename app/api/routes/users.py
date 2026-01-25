from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import UserCreate, UserOut, UserPage, UserUpdate
from app.db.deps import get_mysql_session
from app.services import user_service


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_mysql_session),
):
    return await user_service.create_user(session, payload)


@router.get("", response_model=UserPage)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_mysql_session),
):
    return await user_service.list_users(session, page, size)


@router.get("/raw", response_model=UserPage)
async def list_users_raw(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    username: str | None = Query(None),
    age_min: int | None = Query(None, ge=0),
    age_max: int | None = Query(None, ge=0),
    session: AsyncSession = Depends(get_mysql_session),
):
    return await user_service.list_users_raw(
        session, page, size, username, age_min, age_max
    )


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_mysql_session),
):
    user = await user_service.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_mysql_session),
):
    user = await user_service.update_user(session, user_id, payload)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_mysql_session),
):
    ok = await user_service.delete_user(session, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"deleted": True, "id": user_id}
