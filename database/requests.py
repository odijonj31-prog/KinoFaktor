from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func
from database.db import async_session
from database.models import User, Admin, Channel, Movie, Favorite, VipPlan, VipRequest


# ---------- USERS ----------

async def get_or_create_user(telegram_id: int, username: str | None, full_name: str | None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return user
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_user(telegram_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def is_user_vip(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    if not user or not user.is_vip:
        return False
    if user.vip_expires_at and user.vip_expires_at < datetime.utcnow():
        # muddati o'tgan - avtomatik bekor qilamiz
        async with async_session() as session:
            await session.execute(
                update(User).where(User.telegram_id == telegram_id).values(is_vip=False, vip_plan_name=None)
            )
            await session.commit()
        return False
    return True


async def grant_vip(telegram_id: int, plan_name: str, duration_days: int):
    expires = datetime.utcnow() + timedelta(days=duration_days)
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_vip=True, vip_plan_name=plan_name, vip_expires_at=expires)
        )
        await session.commit()


async def count_users() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(User))
        return result.scalar_one()


async def count_vip_users() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(User).where(User.is_vip == True))
        return result.scalar_one()


async def get_all_user_ids() -> list[int]:
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id).where(User.is_banned == False))
        return [row[0] for row in result.all()]


async def ban_user(telegram_id: int, banned: bool = True):
    async with async_session() as session:
        await session.execute(update(User).where(User.telegram_id == telegram_id).values(is_banned=banned))
        await session.commit()


# ---------- ADMINS ----------

async def is_admin(telegram_id: int, super_admin_id: int) -> bool:
    if telegram_id == super_admin_id:
        return True
    async with async_session() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        return result.scalar_one_or_none() is not None


async def add_admin(telegram_id: int):
    async with async_session() as session:
        session.add(Admin(telegram_id=telegram_id))
        await session.commit()


async def remove_admin(telegram_id: int):
    async with async_session() as session:
        await session.execute(delete(Admin).where(Admin.telegram_id == telegram_id))
        await session.commit()


async def list_admins() -> list[Admin]:
    async with async_session() as session:
        result = await session.execute(select(Admin))
        return list(result.scalars().all())


# ---------- CHANNELS (majburiy obuna) ----------

async def add_channel(chat_id: int, title: str, username: str | None, invite_link: str | None) -> Channel:
    async with async_session() as session:
        ch = Channel(chat_id=chat_id, title=title, username=username, invite_link=invite_link)
        session.add(ch)
        await session.commit()
        await session.refresh(ch)
        return ch


async def get_active_channels() -> list[Channel]:
    async with async_session() as session:
        result = await session.execute(select(Channel).where(Channel.is_active == True))
        return list(result.scalars().all())


async def remove_channel(channel_id: int):
    async with async_session() as session:
        await session.execute(delete(Channel).where(Channel.id == channel_id))
        await session.commit()


async def toggle_channel(channel_id: int, active: bool):
    async with async_session() as session:
        await session.execute(update(Channel).where(Channel.id == channel_id).values(is_active=active))
        await session.commit()


# ---------- MOVIES ----------

async def add_movie(code: str, title: str, file_id: str, description: str | None = None,
                     genre: str | None = None, year: int | None = None,
                     quality: str | None = None, is_vip_only: bool = False) -> Movie:
    async with async_session() as session:
        movie = Movie(code=code, title=title, file_id=file_id, description=description,
                       genre=genre, year=year, quality=quality, is_vip_only=is_vip_only)
        session.add(movie)
        await session.commit()
        await session.refresh(movie)
        return movie


async def get_movie_by_code(code: str) -> Movie | None:
    async with async_session() as session:
        result = await session.execute(select(Movie).where(Movie.code == code))
        return result.scalar_one_or_none()


async def get_movie_by_id(movie_id: int) -> Movie | None:
    async with async_session() as session:
        result = await session.execute(select(Movie).where(Movie.id == movie_id))
        return result.scalar_one_or_none()


async def increment_views(movie_id: int):
    async with async_session() as session:
        await session.execute(update(Movie).where(Movie.id == movie_id).values(views=Movie.views + 1))
        await session.commit()


async def delete_movie(code: str) -> bool:
    async with async_session() as session:
        result = await session.execute(delete(Movie).where(Movie.code == code))
        await session.commit()
        return result.rowcount > 0


async def top_movies(limit: int = 10) -> list[Movie]:
    async with async_session() as session:
        result = await session.execute(select(Movie).order_by(Movie.views.desc()).limit(limit))
        return list(result.scalars().all())


async def search_movies_by_title(query: str, limit: int = 10) -> list[Movie]:
    async with async_session() as session:
        result = await session.execute(
            select(Movie).where(Movie.title.ilike(f"%{query}%")).limit(limit)
        )
        return list(result.scalars().all())


async def count_movies() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(Movie))
        return result.scalar_one()


# ---------- FAVORITES ----------

async def add_favorite(user_id: int, movie_id: int):
    async with async_session() as session:
        exists = await session.execute(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.movie_id == movie_id)
        )
        if exists.scalar_one_or_none():
            return
        session.add(Favorite(user_id=user_id, movie_id=movie_id))
        await session.commit()


async def remove_favorite(user_id: int, movie_id: int):
    async with async_session() as session:
        await session.execute(
            delete(Favorite).where(Favorite.user_id == user_id, Favorite.movie_id == movie_id)
        )
        await session.commit()


async def get_user_favorites(user_id: int) -> list[Movie]:
    async with async_session() as session:
        result = await session.execute(
            select(Movie).join(Favorite, Favorite.movie_id == Movie.id).where(Favorite.user_id == user_id)
        )
        return list(result.scalars().all())


# ---------- VIP PLANS ----------

async def create_vip_plan(name: str, price: int, duration_days: int, description: str | None = None) -> VipPlan:
    async with async_session() as session:
        plan = VipPlan(name=name, price=price, duration_days=duration_days, description=description)
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        return plan


async def get_active_vip_plans() -> list[VipPlan]:
    async with async_session() as session:
        result = await session.execute(select(VipPlan).where(VipPlan.is_active == True))
        return list(result.scalars().all())


async def get_vip_plan(plan_id: int) -> VipPlan | None:
    async with async_session() as session:
        result = await session.execute(select(VipPlan).where(VipPlan.id == plan_id))
        return result.scalar_one_or_none()


# ---------- VIP REQUESTS ----------

async def create_vip_request(user_id: int, plan_id: int, screenshot_file_id: str) -> VipRequest:
    async with async_session() as session:
        req = VipRequest(user_id=user_id, plan_id=plan_id, screenshot_file_id=screenshot_file_id)
        session.add(req)
        await session.commit()
        await session.refresh(req)
        return req


async def get_vip_request(request_id: int) -> VipRequest | None:
    async with async_session() as session:
        result = await session.execute(select(VipRequest).where(VipRequest.id == request_id))
        return result.scalar_one_or_none()


async def update_vip_request_status(request_id: int, status: str):
    async with async_session() as session:
        await session.execute(
            update(VipRequest)
            .where(VipRequest.id == request_id)
            .values(status=status, reviewed_at=datetime.utcnow())
        )
        await session.commit()


async def get_pending_vip_requests() -> list[VipRequest]:
    async with async_session() as session:
        result = await session.execute(select(VipRequest).where(VipRequest.status == "pending"))
        return list(result.scalars().all())
