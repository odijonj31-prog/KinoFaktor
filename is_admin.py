from aiogram.filters import BaseFilter
from aiogram.types import Message
from config import SUPER_ADMIN_ID
from database.requests import is_admin as db_is_admin


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return await db_is_admin(message.from_user.id, SUPER_ADMIN_ID)
