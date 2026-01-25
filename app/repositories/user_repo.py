from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def _build_filters(
    username: str | None,
    age_min: int | None,
    age_max: int | None,
):
    filters: list[str] = []
    params: dict[str, object] = {}

    if username:
        filters.append("username LIKE :username")
        params["username"] = f"%{username}%"
    if age_min is not None:
        filters.append("age >= :age_min")
        params["age_min"] = age_min
    if age_max is not None:
        filters.append("age <= :age_max")
        params["age_max"] = age_max

    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
    return where_clause, params


async def create_user(session: AsyncSession, user: User) -> User:
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def list_users(session: AsyncSession, page: int, size: int) -> tuple[int, list[User]]:
    total = await session.scalar(select(func.count()).select_from(User))
    result = await session.execute(
        select(User)
        .order_by(User.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return int(total or 0), result.scalars().all()


async def list_users_raw(
    session: AsyncSession,
    page: int,
    size: int,
    username: str | None,
    age_min: int | None,
    age_max: int | None,
) -> tuple[int, list[dict]]:
    where_clause, params = _build_filters(username, age_min, age_max)

    total_sql = text(f"SELECT COUNT(1) AS total FROM t_user{where_clause}")
    total = await session.scalar(total_sql, params)

    data_sql = text(
        "SELECT id, username, password, age, ext_json, create_time "
        f"FROM t_user{where_clause} ORDER BY id DESC LIMIT :limit OFFSET :offset"
    )
    params_with_page = dict(params)
    params_with_page["limit"] = size
    params_with_page["offset"] = (page - 1) * size

    result = await session.execute(data_sql, params_with_page)
    rows = result.mappings().all()
    return int(total or 0), [dict(row) for row in rows]


async def update_user(session: AsyncSession, user: User) -> User:
    await session.commit()
    await session.refresh(user)
    return user


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()
