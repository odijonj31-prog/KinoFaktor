from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import SUPER_ADMIN_IDS
from database.requests import (
    get_active_vip_plans, get_vip_plan, create_vip_request, get_user,
    list_admins, is_user_vip
)
from keyboards.user_kb import vip_plans_kb, vip_payment_confirm_kb, admin_vip_review_kb
from states import VipPurchase

router = Router()

# To'lov qabul qilinadigan karta raqami - o'zgartiring
PAYMENT_CARD_INFO = "💳 8600 3329 7311 9468 (Sh.Majidov)"


@router.message(F.text == "👑 VIP")
async def show_vip_menu(message: Message):
    if await is_user_vip(message.from_user.id):
        user = await get_user(message.from_user.id)
        expires = user.vip_expires_at.strftime("%d.%m.%Y") if user.vip_expires_at else "—"
        await message.answer(
            f"👑 Siz allaqachon <b>{user.vip_plan_name}</b> VIP obunasiga egasiz!\n"
            f"📅 Amal qilish muddati: {expires}"
        )
        return

    plans = await get_active_vip_plans()
    if not plans:
        await message.answer("Hozircha VIP tariflar mavjud emas.")
        return

    text = "👑 <b>VIP obuna rejalari</b>\n\nO'zingizga ma'qul tarif rejasini tanlang:\n\n"
    for p in plans:
        text += f"<b>{p.name}</b> — {p.price:,} so'm / {p.duration_days} kun\n".replace(",", " ")
        if p.description:
            text += f"{p.description}\n"
        text += "\n"

    await message.answer(text, reply_markup=vip_plans_kb(plans))


@router.callback_query(F.data.startswith("vip_buy:"))
async def vip_buy(callback: CallbackQuery):
    plan_id = int(callback.data.split(":")[1])
    plan = await get_vip_plan(plan_id)
    if not plan:
        await callback.answer("Tarif topilmadi.", show_alert=True)
        return
    price_line = f"👑 <b>{plan.name}</b> tarifi — {plan.price:,} so'm / {plan.duration_days} kun\n\n".replace(",", " ")
    await callback.message.answer(
        price_line +
        f"To'lovni quyidagi kartaga o'tkazing:\n{PAYMENT_CARD_INFO}\n\n"
        f"To'lovni amalga oshirgach, chek skrinshotini yuboring.",
        reply_markup=vip_payment_confirm_kb(plan_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vip_send_receipt:"))
async def ask_receipt(callback: CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split(":")[1])
    await state.update_data(plan_id=plan_id)
    await state.set_state(VipPurchase.waiting_receipt)
    await callback.message.answer("📤 Endi to'lov chekining skrinshotini (rasm) shu yerga yuboring:")
    await callback.answer()


@router.callback_query(F.data == "vip_back")
async def vip_back(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.message(VipPurchase.waiting_receipt, F.photo)
async def process_receipt(message: Message, bot: Bot, state: FSMContext):
    data = await state.get_data()
    plan_id = data.get("plan_id")
    await state.clear()

    plan = await get_vip_plan(plan_id)
    user = await get_user(message.from_user.id)
    if not plan or not user:
        await message.answer("Xatolik yuz berdi, qaytadan urinib ko'ring.")
        return

    screenshot_file_id = message.photo[-1].file_id
    req = await create_vip_request(user.id, plan.id, screenshot_file_id)

    await message.answer(
        "✅ Chekingiz qabul qilindi va admin ko'rib chiqishi uchun yuborildi.\n"
        "⏳ Tez orada tasdiqlanadi, iltimos kuting."
    )

    # Barcha adminlarga yuborish
    admin_ids = {SUPER_ADMIN_ID} | {a.telegram_id for a in await list_admins()}
    caption = (
        f"🆕 <b>Yangi VIP so'rov</b>\n\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name} (@{message.from_user.username or '—'})\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"👑 Tarif: {plan.name} — {plan.price:,} so'm / {plan.duration_days} kun\n"
        f"🔢 So'rov ID: {req.id}"
    ).replace(",", " ")

    for admin_id in admin_ids:
        try:
            await bot.send_photo(
                admin_id, photo=screenshot_file_id, caption=caption,
                reply_markup=admin_vip_review_kb(req.id),
            )
        except Exception:
            pass


@router.message(VipPurchase.waiting_receipt)
async def receipt_wrong_type(message: Message):
    await message.answer("❗️ Iltimos, chekning rasmini (skrinshot) yuboring.")
