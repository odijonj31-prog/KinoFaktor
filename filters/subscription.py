from aiogram import Bot
from aiogram.types import User
from database.models import Channel
from database.requests import get_active_channels


async def get_unsubscribed_channels(bot: Bot, user_id: int) -> list[Channel]:
    """Foydalanuvchi obuna bo'lmagan faol kanallar ro'yxatini qaytaradi."""
    channels = await get_active_channels()
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch.chat_id, user_id=user_id)
            if member.status in ("left", "kicked"):
                not_subscribed.append(ch)
        except Exception:
            # Bot kanalda admin bo'lmasa yoki xatolik bo'lsa - xavfsizlik uchun obuna bo'lmagan deb hisoblaymiz
            not_subscribed.append(ch)
    return not_subscribed
