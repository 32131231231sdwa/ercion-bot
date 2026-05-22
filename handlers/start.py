import os
import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy import select, func

from models.database import async_session_maker, User, Race, Country, get_setting
from keyboards.menus import main_menu, subscribe_keyboard, back_to_menu
from utils.helpers import is_admin, CHANNEL_USERNAME, safe_edit

logger = logging.getLogger(__name__)
router = Router()

MENU_IMAGE = "media/menu.jpg"


async def check_subscription(bot: Bot, user_id: int) -> bool:
    if not CHANNEL_USERNAME:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception as e:
        logger.warning(f"Sub check failed: {e}")
        return True


async def get_or_create_user(user_id: int, username: str, first_name: str):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=user_id, username=username, first_name=first_name)
            session.add(user)
            await session.commit()
        return user


async def get_pending_count() -> int:
    async with async_session_maker() as session:
        race_count = await session.scalar(select(func.count(Race.id)).where(Race.status == "pending"))
        country_count = await session.scalar(select(func.count(Country.id)).where(Country.status == "pending"))
        return (race_count or 0) + (country_count or 0)


async def send_main_menu(target, bot: Bot, user_id: int):
    admin = is_admin(user_id)
    pending = await get_pending_count() if admin else 0

    caption = "⚔️ <b>Добро пожаловать в Эрцион III Season</b>\n\nВыбери раздел для продолжения своего пути."
    if admin and pending > 0:
        caption += f"\n\n🔔 Непроверенных заявок: <b>{pending}</b>"

    keyboard = main_menu(admin)

    try:
        photo = FSInputFile(MENU_IMAGE)
        await target.answer_photo(photo=photo, caption=caption, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Could not send photo menu: {e}")
        text = "⚔️ <b>Эрцион III Season</b>\n\nВыбери раздел."
        if admin and pending > 0:
            text += f"\n\n🔔 Заявок: <b>{pending}</b>"
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    if message.chat.type != "private":
        await message.answer("📜 Используй бота в личных сообщениях.", parse_mode="HTML")
        return

    await get_or_create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or ""
    )

    subscribed = await check_subscription(bot, message.from_user.id)
    if not subscribed:
        await message.answer(
            "📜 Для доступа к боту необходимо подписаться на канал Эрциона.",
            reply_markup=subscribe_keyboard(CHANNEL_USERNAME),
            parse_mode="HTML"
        )
        return

    await send_main_menu(message, bot, message.from_user.id)


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, bot: Bot):
    subscribed = await check_subscription(bot, callback.from_user.id)
    if not subscribed:
        await callback.answer("Ты ещё не подписался на канал!", show_alert=True)
        return
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_main_menu(callback.message, bot, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, bot: Bot):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_main_menu(callback.message, bot, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "rules")
async def rules_callback(callback: CallbackQuery):
    text = await get_setting("rules")
    await safe_edit(callback.message, text, back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "changelog")
async def changelog_callback(callback: CallbackQuery):
    text = await get_setting("changelog")
    await safe_edit(callback.message, text, back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "start_conditions")
async def start_conditions_callback(callback: CallbackQuery):
    text = await get_setting("start_conditions")
    await safe_edit(callback.message, text, back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "minerals")
async def minerals_callback(callback: CallbackQuery):
    text = await get_setting("minerals")
    await safe_edit(callback.message, text, back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    text = await get_setting("help")
    await safe_edit(callback.message, text, back_to_menu())
    await callback.answer()
