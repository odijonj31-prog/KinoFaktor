from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Channel, VipPlan, Movie


def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🔍 Kino qidirish"), KeyboardButton(text="🏆 TOP filmlar")],
        [KeyboardButton(text="🔖 Saqlanganlar"), KeyboardButton(text="👑 VIP")],
        [KeyboardButton(text="💡 Yordam")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def subscription_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        url = ch.invite_link or f"https://t.me/{ch.username.lstrip('@')}" if ch.username else ch.invite_link
        builder.row(InlineKeyboardButton(text=f"🔒 {ch.title}", url=url))
    builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription"))
    return builder.as_markup()


def vip_plans_kb(plans: list[VipPlan]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.row(InlineKeyboardButton(
            text=f"{plan.name} — {plan.price:,} so'm / {plan.duration_days} kun".replace(",", " "),
            callback_data=f"vip_buy:{plan.id}"
        ))
    return builder.as_markup()


def vip_payment_confirm_kb(plan_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 To'lov chekini yuborish", callback_data=f"vip_send_receipt:{plan_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="vip_back"))
    return builder.as_markup()


def movie_actions_kb(movie: Movie, is_favorite: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    fav_text = "💔 Sevimlilardan olib tashlash" if is_favorite else "❤️ Sevimlilarga qo'shish"
    builder.row(InlineKeyboardButton(text=fav_text, callback_data=f"fav_toggle:{movie.id}"))
    return builder.as_markup()


def admin_vip_review_kb(request_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"vip_approve:{request_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"vip_reject:{request_id}"),
    )
    return builder.as_markup()
