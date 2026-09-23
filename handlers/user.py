from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.requests import (
    get_or_create_user, get_movie_by_code, increment_views, add_favorite,
    remove_favorite, get_user_favorites, get_user, top_movies, is_user_vip
)
from filters.subscription import get_unsubscribed_channels
from keyboards.user_kb import main_menu_kb, subscription_kb, movie_actions_kb
from states import SearchMovie

router = Router()


async def send_movie(message: Message, movie, user_id: int):
    favs = await get_user_favorites(user_id)
    is_fav = any(m.id == movie.id for m in favs)
    caption = f"🎬 <b>{movie.title}</b>\n"
    if movie.year:
        caption += f"📅 Yil: {movie.year}\n"
    if movie.genre:
        caption += f"🎭 Janr: {movie.genre}\n"
    if movie.quality:
        caption += f"📀 Sifat: {movie.quality}\n"
    if movie.description:
        caption += f"\n{movie.description}\n"
    caption += f"\n👁 Ko'rishlar: {movie.views}"

    await message.answer_video(
        video=movie.file_id,
        caption=caption,
        reply_markup=movie_actions_kb(movie, is_fav),
    )
    await increment_views(movie.id)


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    unsubscribed = await get_unsubscribed_channels(bot, message.from_user.id)
    if unsubscribed:
        await message.answer(
            "👋 Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling!\n\n"
            "👑 Yoki <b>VIP</b> obunasini sotib oling va botdan hech qanday kanallarga "
            "obuna bo'lmasdan, cheklovlarsiz foydalaning!",
            reply_markup=subscription_kb(unsubscribed),
        )
        return

    await message.answer(
        f"👋 Assalomu alaykum, {message.from_user.first_name}!\n"
        f"🍿 Bot orqali minglab kino, serial va multfilmlarni yuqori sifatda tomosha qiling!\n\n"
        f"🚀 Foydalanish juda oson!\n"
        f"- O'zingizga kerakli <b>Film kodini</b> yuboring\n"
        f"- Qulay bo'limlar orqali qidiring\n"
        f"- <b>VIP</b> bilan cheklovlarsiz foydalaning",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    unsubscribed = await get_unsubscribed_channels(bot, callback.from_user.id)
    if unsubscribed:
        await callback.answer("❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)
        return
    await callback.message.delete()
    await callback.message.answer(
        "✅ Rahmat! Endi botdan to'liq foydalanishingiz mumkin.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.message(F.text == "🔍 Kino qidirish")
async def ask_movie_code(message: Message, state: FSMContext):
    await state.set_state(SearchMovie.waiting_code)
    await message.answer("🎬 Kino kodini kiriting (masalan: <code>1234</code>):")


@router.message(SearchMovie.waiting_code)
async def process_movie_code(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    code = message.text.strip()

    unsubscribed = await get_unsubscribed_channels(bot, message.from_user.id)
    if unsubscribed:
        await message.answer(
            "🔒 Kinolarni ko'rish uchun avval kanallarga obuna bo'ling:",
            reply_markup=subscription_kb(unsubscribed),
        )
        return

    movie = await get_movie_by_code(code)
    if not movie:
        await message.answer("❌ Bunday kodli kino topilmadi. Kodni tekshirib qayta urinib ko'ring.")
        return

    if movie.is_vip_only and not await is_user_vip(message.from_user.id):
        await message.answer(
            "👑 Bu kino faqat VIP foydalanuvchilar uchun!\n"
            "VIP tariflarni ko'rish uchun «👑 VIP» tugmasini bosing."
        )
        return

    await send_movie(message, movie, message.from_user.id)


# Kino kodini to'g'ridan-to'g'ri, menyusiz yuborsa ham ishlashi uchun
@router.message(F.text.regexp(r"^[A-Za-z0-9_\-]{2,20}$"))
async def direct_code_search(message: Message, bot: Bot, state: FSMContext):
    if await state.get_state() is not None:
        return
    movie = await get_movie_by_code(message.text.strip())
    if not movie:
        return  # oddiy matn bo'lishi mumkin, e'tiborsiz qoldiramiz
    unsubscribed = await get_unsubscribed_channels(bot, message.from_user.id)
    if unsubscribed:
        await message.answer("🔒 Kinolarni ko'rish uchun avval kanallarga obuna bo'ling:",
                              reply_markup=subscription_kb(unsubscribed))
        return
    if movie.is_vip_only and not await is_user_vip(message.from_user.id):
        await message.answer("👑 Bu kino faqat VIP foydalanuvchilar uchun!")
        return
    await send_movie(message, movie, message.from_user.id)


@router.message(F.text == "🏆 TOP filmlar")
async def show_top_movies(message: Message):
    movies = await top_movies(10)
    if not movies:
        await message.answer("Hozircha kinolar qo'shilmagan.")
        return
    text = "🏆 <b>TOP 10 kino</b>\n\n"
    for i, m in enumerate(movies, 1):
        text += f"{i}. <code>{m.code}</code> — {m.title} (👁 {m.views})\n"
    text += "\nKo'rish uchun kodni yuboring."
    await message.answer(text)


@router.message(F.text == "🔖 Saqlanganlar")
async def show_favorites(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing.")
        return
    movies = await get_user_favorites(user.id)
    if not movies:
        await message.answer("🔖 Sizda hali saqlangan kinolar yo'q.")
        return
    text = "🔖 <b>Sizning saqlangan kinolaringiz</b>\n\n"
    for m in movies:
        text += f"• <code>{m.code}</code> — {m.title}\n"
    text += "\nKo'rish uchun kodni yuboring."
    await message.answer(text)


@router.callback_query(F.data.startswith("fav_toggle:"))
async def toggle_favorite(callback: CallbackQuery):
    movie_id = int(callback.data.split(":")[1])
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return
    favs = await get_user_favorites(user.id)
    if any(m.id == movie_id for m in favs):
        await remove_favorite(user.id, movie_id)
        await callback.answer("💔 Sevimlilardan olib tashlandi")
    else:
        await add_favorite(user.id, movie_id)
        await callback.answer("❤️ Sevimlilarga qo'shildi")


@router.message(F.text == "💡 Yordam")
async def show_help(message: Message):
    await message.answer(
        "💡 <b>Yordam</b>\n\n"
        "🔍 Kino qidirish — kino kodini kiritib qidiring\n"
        "🏆 TOP filmlar — eng ko'p ko'rilgan kinolar\n"
        "🔖 Saqlanganlar — sevimli kinolaringiz\n"
        "👑 VIP — cheklovlarsiz foydalanish\n\n"
        "Savol va takliflar uchun: @your_support_username"
    )
