from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import SUPER_ADMIN_ID
from filters.is_admin import IsAdmin
from states import AddMovie, DeleteMovie, AddChannel, Broadcast, AddVipPlan
from keyboards.admin_kb import admin_menu_kb, channels_list_kb, confirm_broadcast_kb
from keyboards.user_kb import main_menu_kb
from database.requests import (
    add_movie, delete_movie, add_channel, get_active_channels, remove_channel,
    toggle_channel, count_users, count_vip_users, count_movies, get_all_user_ids,
    get_vip_request, update_vip_request_status, grant_vip, get_user, ban_user,
    create_vip_plan, get_active_vip_plans, get_pending_vip_requests,
)

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def open_admin_panel(message: Message):
    await message.answer("🛠 Admin panelga xush kelibsiz!", reply_markup=admin_menu_kb())


@router.message(F.text == "⬅️ Foydalanuvchi menyusi")
async def back_to_user_menu(message: Message):
    await message.answer("Foydalanuvchi menyusiga qaytdingiz.", reply_markup=main_menu_kb())


# ---------- KINO QO'SHISH ----------

@router.message(F.text == "🎬 Kino qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    await state.set_state(AddMovie.waiting_video)
    await message.answer("🎬 Kino videosini (fayl sifatida) yuboring:")


@router.message(AddMovie.waiting_video, F.video)
async def add_movie_video(message: Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await state.set_state(AddMovie.waiting_code)
    await message.answer("🔢 Kino uchun kod kiriting (masalan: 1001):")


@router.message(AddMovie.waiting_video)
async def add_movie_video_wrong(message: Message):
    await message.answer("❗️ Iltimos, video fayl yuboring.")


@router.message(AddMovie.waiting_code)
async def add_movie_code(message: Message, state: FSMContext):
    from database.requests import get_movie_by_code
    code = message.text.strip()
    existing = await get_movie_by_code(code)
    if existing:
        await message.answer("❌ Bu kod band. Boshqa kod kiriting:")
        return
    await state.update_data(code=code)
    await state.set_state(AddMovie.waiting_title)
    await message.answer("📝 Kino nomini kiriting:")


@router.message(AddMovie.waiting_title)
async def add_movie_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddMovie.waiting_description)
    await message.answer("📄 Kino haqida qisqacha ma'lumot kiriting (yoki /skip):")


@router.message(AddMovie.waiting_description, Command("skip"))
async def add_movie_desc_skip(message: Message, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(AddMovie.waiting_vip_only)
    await message.answer("👑 Bu kino faqat VIP uchunmi? (ha / yo'q)")


@router.message(AddMovie.waiting_description)
async def add_movie_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddMovie.waiting_vip_only)
    await message.answer("👑 Bu kino faqat VIP uchunmi? (ha / yo'q)")


@router.message(AddMovie.waiting_vip_only)
async def add_movie_vip_only(message: Message, state: FSMContext):
    is_vip = message.text.strip().lower() in ("ha", "ha.", "yes", "+")
    data = await state.get_data()
    await state.clear()

    movie = await add_movie(
        code=data["code"], title=data["title"], file_id=data["file_id"],
        description=data.get("description"), is_vip_only=is_vip,
    )
    await message.answer(
        f"✅ Kino qo'shildi!\n\n🎬 {movie.title}\n🔢 Kod: <code>{movie.code}</code>\n"
        f"👑 VIP only: {'Ha' if is_vip else "Yo'q"}",
        reply_markup=admin_menu_kb(),
    )


# ---------- KINO O'CHIRISH ----------

@router.message(F.text == "🗑 Kino o'chirish")
async def delete_movie_start(message: Message, state: FSMContext):
    await state.set_state(DeleteMovie.waiting_code)
    await message.answer("🔢 O'chirmoqchi bo'lgan kino kodini kiriting:")


@router.message(DeleteMovie.waiting_code)
async def delete_movie_process(message: Message, state: FSMContext):
    await state.clear()
    code = message.text.strip()
    ok = await delete_movie(code)
    if ok:
        await message.answer(f"✅ <code>{code}</code> kodli kino o'chirildi.", reply_markup=admin_menu_kb())
    else:
        await message.answer("❌ Bunday kodli kino topilmadi.", reply_markup=admin_menu_kb())


# ---------- KANALLAR ----------

@router.message(F.text == "📢 Kanal qo'shish")
async def add_channel_start(message: Message, state: FSMContext):
    await state.set_state(AddChannel.waiting_forward_or_id)
    await message.answer(
        "📢 Botni kanalga <b>admin</b> qilib qo'shing, so'ng kanaldan istalgan xabarni "
        "shu yerga forward qiling.\n\nYoki kanal ID sini <code>-100xxxxxxxxxx</code> formatida yuboring."
    )


@router.message(AddChannel.waiting_forward_or_id, F.forward_from_chat)
async def add_channel_forward(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    chat = message.forward_from_chat
    try:
        await bot.get_chat_member(chat.id, bot.id)
    except Exception:
        await message.answer("❌ Bot ushbu kanalda admin emas. Avval botni admin qiling.")
        return

    invite_link = None
    if not chat.username:
        try:
            invite_link = await bot.export_chat_invite_link(chat.id)
        except Exception:
            pass

    ch = await add_channel(chat_id=chat.id, title=chat.title, username=chat.username, invite_link=invite_link)
    await message.answer(f"✅ Kanal qo'shildi: {ch.title}", reply_markup=admin_menu_kb())


@router.message(AddChannel.waiting_forward_or_id, F.text)
async def add_channel_by_id(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Qaytadan urinib ko'ring.", reply_markup=admin_menu_kb())
        return
    try:
        chat = await bot.get_chat(chat_id)
        await bot.get_chat_member(chat_id, bot.id)
    except Exception:
        await message.answer("❌ Kanal topilmadi yoki bot u yerda admin emas.", reply_markup=admin_menu_kb())
        return

    invite_link = None
    if not chat.username:
        try:
            invite_link = await bot.export_chat_invite_link(chat_id)
        except Exception:
            pass

    ch = await add_channel(chat_id=chat.id, title=chat.title, username=chat.username, invite_link=invite_link)
    await message.answer(f"✅ Kanal qo'shildi: {ch.title}", reply_markup=admin_menu_kb())


@router.message(F.text == "📋 Kanallar ro'yxati")
async def list_channels(message: Message):
    channels = await get_active_channels()
    if not channels:
        await message.answer("Hozircha kanallar qo'shilmagan.")
        return
    await message.answer("📋 <b>Majburiy obuna kanallari:</b>", reply_markup=channels_list_kb(channels))


@router.callback_query(F.data.startswith("admin_ch_toggle:"))
async def toggle_channel_cb(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    channels = await get_active_channels()
    ch = next((c for c in channels if c.id == channel_id), None)
    if ch:
        await toggle_channel(channel_id, not ch.is_active)
    channels = await get_active_channels()
    await callback.message.edit_reply_markup(reply_markup=channels_list_kb(channels))
    await callback.answer("Holat o'zgartirildi")


@router.callback_query(F.data.startswith("admin_ch_delete:"))
async def delete_channel_cb(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    await remove_channel(channel_id)
    channels = await get_active_channels()
    await callback.message.edit_reply_markup(reply_markup=channels_list_kb(channels))
    await callback.answer("Kanal o'chirildi")


# ---------- STATISTIKA ----------

@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    users = await count_users()
    vip = await count_vip_users()
    movies = await count_movies()
    channels = await get_active_channels()
    pending = await get_pending_vip_requests()
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"👑 VIP foydalanuvchilar: {vip}\n"
        f"🎬 Kinolar soni: {movies}\n"
        f"📢 Faol kanallar: {len(channels)}\n"
        f"⏳ Kutilayotgan VIP so'rovlar: {len(pending)}"
    )


# ---------- BROADCAST ----------

@router.message(F.text == "📨 Xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    await state.set_state(Broadcast.waiting_content)
    await message.answer("📨 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:")


@router.message(Broadcast.waiting_content)
async def broadcast_preview(message: Message, state: FSMContext):
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(Broadcast.waiting_confirm)
    await message.answer("Yuqoridagi xabarni barchaga yuborishni tasdiqlaysizmi?", reply_markup=confirm_broadcast_kb())


@router.callback_query(Broadcast.waiting_confirm, F.data == "broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, bot: Bot, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    user_ids = await get_all_user_ids()

    sent, failed = 0, 0
    await callback.message.edit_text(f"⏳ Yuborilmoqda... (0/{len(user_ids)})")
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=data["chat_id"], message_id=data["message_id"])
            sent += 1
        except Exception:
            failed += 1
    await callback.message.edit_text(f"✅ Yuborildi: {sent}\n❌ Yuborilmadi: {failed}")


@router.callback_query(Broadcast.waiting_confirm, F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")


# ---------- VIP TASDIQLASH ----------

@router.callback_query(F.data.startswith("vip_approve:"))
async def vip_approve(callback: CallbackQuery, bot: Bot):
    request_id = int(callback.data.split(":")[1])
    req = await get_vip_request(request_id)
    if not req or req.status != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    from database.requests import get_vip_plan as _get_plan
    plan = await _get_plan(req.plan_id)
    user = await get_user_by_row_id(req.user_id)

    await update_vip_request_status(request_id, "approved")
    await grant_vip(user.telegram_id, plan.name, plan.duration_days)

    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ <b>TASDIQLANDI</b>")
    await callback.answer("Tasdiqlandi")

    try:
        await bot.send_message(
            user.telegram_id,
            f"🎉 Tabriklaymiz! Sizning <b>{plan.name}</b> VIP obunangiz faollashtirildi!\n"
            f"📅 Muddat: {plan.duration_days} kun"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("vip_reject:"))
async def vip_reject(callback: CallbackQuery, bot: Bot):
    request_id = int(callback.data.split(":")[1])
    req = await get_vip_request(request_id)
    if not req or req.status != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    user = await get_user_by_row_id(req.user_id)
    await update_vip_request_status(request_id, "rejected")

    await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ <b>RAD ETILDI</b>")
    await callback.answer("Rad etildi")

    try:
        await bot.send_message(
            user.telegram_id,
            "❌ Sizning VIP to'lov chekingiz rad etildi. Savollar uchun admin bilan bog'laning."
        )
    except Exception:
        pass


async def get_user_by_row_id(user_row_id: int):
    """VipRequest.user_id — bu users jadvalidagi PK (id), telegram_id emas."""
    from database.db import async_session
    from database.models import User
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_row_id))
        return result.scalar_one()


# ---------- VIP TARIFLAR ----------

@router.message(F.text == "💳 VIP tariflar")
async def vip_plans_menu(message: Message, state: FSMContext):
    plans = await get_active_vip_plans()
    text = "💳 <b>Mavjud VIP tariflar:</b>\n\n"
    if plans:
        for p in plans:
            text += f"• {p.name} — {p.price:,} so'm / {p.duration_days} kun\n".replace(",", " ")
    else:
        text += "Hozircha tarif qo'shilmagan.\n"
    text += "\nYangi tarif qo'shish uchun /addplan buyrug'ini yuboring."
    await message.answer(text)


@router.message(Command("addplan"))
async def add_plan_start(message: Message, state: FSMContext):
    await state.set_state(AddVipPlan.waiting_name)
    await message.answer("📝 Tarif nomini kiriting (masalan: START):")


@router.message(AddVipPlan.waiting_name)
async def add_plan_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddVipPlan.waiting_price)
    await message.answer("💰 Narxini so'mda kiriting (masalan: 7900):")


@router.message(AddVipPlan.waiting_price)
async def add_plan_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip().replace(" ", ""))
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.")
        return
    await state.update_data(price=price)
    await state.set_state(AddVipPlan.waiting_duration)
    await message.answer("📅 Necha kunlik obuna? (masalan: 30):")


@router.message(AddVipPlan.waiting_duration)
async def add_plan_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.")
        return
    data = await state.get_data()
    await state.clear()
    plan = await create_vip_plan(name=data["name"], price=data["price"], duration_days=duration)
    await message.answer(f"✅ Tarif qo'shildi: {plan.name} — {plan.price:,} so'm / {plan.duration_days} kun".replace(",", " "),
                          reply_markup=admin_menu_kb())
