from datetime import datetime
from sqlalchemy import (
    BigInteger, String, Integer, Boolean, DateTime, ForeignKey, Text, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    vip_plan_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vip_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Channel(Base):
    """Majburiy obuna talab qilinadigan kanallar."""
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)   # -100xxxxxxxxxx
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)  # @kanal (invite link bo'lsa None)
    invite_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(String(128), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    file_id: Mapped[str] = mapped_column(String(255))   # telegram video file_id
    quality: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 720p / 1080p
    is_vip_only: Mapped[bool] = mapped_column(Boolean, default=False)

    views: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    favorited_by: Mapped[list["Favorite"]] = relationship(back_populates="movie")


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="favorites")
    movie: Mapped["Movie"] = relationship(back_populates="favorited_by")


class VipPlan(Base):
    __tablename__ = "vip_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))          # START / PLUS / PRO
    price: Mapped[int] = mapped_column(Integer)             # so'mda
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class VipRequest(Base):
    """Foydalanuvchi VIP sotib olish uchun chek yuborganda shu yerga tushadi."""
    __tablename__ = "vip_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("vip_plans.id"))
    screenshot_file_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approved/rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship()
    plan: Mapped["VipPlan"] = relationship()
