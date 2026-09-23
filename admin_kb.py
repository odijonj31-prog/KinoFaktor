from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Channel


def admin_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🎬 Kino qo'shish"), KeyboardButton(text="🗑 Kino o'chirish")],
        [KeyboardButton(text="📢 Kanal qo'shish"), KeyboardButton(text="📋 Kanallar ro'yxati")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📨 Xabar yuborish")],
        [KeyboardButton(text="👑 VIP so'rovlar"), KeyboardButton(text="💳 VIP tariflar")],
        [KeyboardButton(text="⬅️ Foydalanuvchi menyusi")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def channels_list_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        status = "🟢" if ch.is_active else "🔴"
        builder.row(InlineKeyboardButton(text=f"{status} {ch.title}", callback_data=f"admin_ch_toggle:{ch.id}"),
                    InlineKeyboardButton(text="🗑", callback_data=f"admin_ch_delete:{ch.id}"))
    return builder.as_markup()


def confirm_broadcast_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel"),
    )
    return builder.as_markup()
