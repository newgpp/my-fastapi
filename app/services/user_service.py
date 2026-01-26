import json
import random

from app.models.user import User
from app.repositories import user_repo
from app.schemas import UserCreate, UserOut, UserPage, UserUpdate
from sqlalchemy.ext.asyncio import AsyncSession


def _serialize_ext_json(value: dict | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _deserialize_ext_json(value: str | None) -> dict | None:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _to_schema(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        password=user.password,
        age=user.age,
        ext_json=_deserialize_ext_json(user.ext_json),
        create_time=user.create_time,
    )


async def create_user(session: AsyncSession, payload: UserCreate) -> UserOut:
    user = User(
        username=payload.username,
        password=payload.password,
        age=payload.age,
        ext_json=_serialize_ext_json(payload.ext_json),
    )
    user = await user_repo.create_user(session, user)
    return _to_schema(user)


async def get_user(session: AsyncSession, user_id: int) -> UserOut | None:
    user = await user_repo.get_user_by_id(session, user_id)
    if user is None:
        return None
    return _to_schema(user)


async def list_users(session: AsyncSession, page: int, size: int) -> UserPage:
    total, users = await user_repo.list_users(session, page, size)
    return UserPage(
        total=total,
        page=page,
        size=size,
        items=[_to_schema(u) for u in users],
    )


async def list_users_raw(
    session: AsyncSession,
    page: int,
    size: int,
    username: str | None,
    age_min: int | None,
    age_max: int | None,
) -> UserPage:
    total, rows = await user_repo.list_users_raw(
        session, page, size, username, age_min, age_max
    )
    items = [
        UserOut(
            id=row["id"],
            username=row["username"],
            password=row["password"],
            age=row["age"],
            ext_json=_deserialize_ext_json(row["ext_json"]),
            create_time=row["create_time"],
        )
        for row in rows
    ]
    return UserPage(total=total, page=page, size=size, items=items)


async def update_user(
    session: AsyncSession,
    user_id: int,
    payload: UserUpdate,
) -> UserOut | None:
    user = await user_repo.get_user_by_id(session, user_id)
    if user is None:
        return None

    data = payload.model_dump(exclude_unset=True)
    if "ext_json" in data:
        data["ext_json"] = _serialize_ext_json(data["ext_json"])

    for key, value in data.items():
        setattr(user, key, value)

    user = await user_repo.update_user(session, user)
    return _to_schema(user)


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    # 1. 先查出对象
    user = await user_repo.get_user_by_id(session, user_id)
    if not user:
        return False
    
    try:
        # 如果你确定外部没开事务，用 begin()；
        # 如果不确定，推荐在调用此函数的地方管理事务。
        async with session.begin_nested(): # 使用保存点，更安全
            await session.delete(user)
            if random.getrandbits(1):
                raise RuntimeError("Simulated failure")
        
        # 如果没有用 begin() 装饰器，则需要手动 commit
        await session.commit() 
        return True
    except Exception:
        await session.rollback() # 发生异常务必回滚
        return False

