import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from models.database import async_session_maker, Race, Country, get_setting
from utils.helpers import paginate

logger = logging.getLogger(__name__)
router = Router()

# Группо-команды работают везде, но регистрация — только в ЛС


def dm_button(bot_username: str = "") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if bot_username:
        builder.row(InlineKeyboardButton(text="✉️ Открыть в ЛС", url=f"https://t.me/{bot_username}"))
    return builder.as_markup()


async def get_bot_username(bot: Bot) -> str:
    try:
        me = await bot.get_me()
        return me.username or ""
    except Exception:
        return ""


# ─── /help ────────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message, bot: Bot):
    text = await get_setting("help")
    username = await get_bot_username(bot)
    builder = InlineKeyboardBuilder()
    if username and message.chat.type != "private":
        builder.row(InlineKeyboardButton(text="✉️ Открыть меню в ЛС", url=f"https://t.me/{username}"))
    kb = builder.as_markup() if username and message.chat.type != "private" else None
    await message.answer(text, reply_markup=kb)


# ─── /rules ───────────────────────────────────────────────────────────────────

@router.message(Command("rules"))
async def cmd_rules(message: Message):
    text = await get_setting("rules")
    await message.answer(text)


# ─── /news ────────────────────────────────────────────────────────────────────

@router.message(Command("news"))
async def cmd_news(message: Message):
    text = await get_setting("changelog")
    await message.answer(text)


# ─── /start_conditions ────────────────────────────────────────────────────────

@router.message(Command("start_conditions"))
async def cmd_start_conditions(message: Message):
    text = await get_setting("start_conditions")
    await message.answer(text)


# ─── /minerals ────────────────────────────────────────────────────────────────

@router.message(Command("minerals"))
async def cmd_minerals(message: Message):
    text = await get_setting("minerals")
    await message.answer(text)


# ─── /races ───────────────────────────────────────────────────────────────────

@router.message(Command("races"))
async def cmd_races(message: Message, bot: Bot):
    async with async_session_maker() as session:
        result = await session.execute(
            select(Race).where(Race.is_approved == True).order_by(Race.is_custom, Race.name)
        )
        races = result.scalars().all()

    if not races:
        await message.answer("🧝 Расы пока не добавлены.")
        return

    text = "🧝 <b>Расы Эрциона</b>\n\n"
    for race in races:
        icon = "👑" if not race.is_custom else "🧬"
        text += f"{icon} <b>{race.name}</b>"
        if race.features:
            short = race.features[:60] + "…" if len(race.features) > 60 else race.features
            text += f"\n<i>{short}</i>"
        text += "\n\n"

    username = await get_bot_username(bot)
    builder = InlineKeyboardBuilder()
    if username:
        builder.row(InlineKeyboardButton(text="📖 Подробнее в ЛС", url=f"https://t.me/{username}"))
        builder.row(InlineKeyboardButton(text="✍ Зарегистрировать расу", url=f"https://t.me/{username}"))

    await message.answer(text[:4096], reply_markup=builder.as_markup() if username else None)


# ─── /countries ───────────────────────────────────────────────────────────────

@router.message(Command("countries"))
async def cmd_countries(message: Message, bot: Bot):
    async with async_session_maker() as session:
        result = await session.execute(
            select(Country).where(Country.is_approved == True).order_by(Country.name)
        )
        countries = result.scalars().all()

    if not countries:
        await message.answer("🗾 Одобренных стран пока нет.\n\nОснуй свою в ЛС бота!")
        return

    text = "🗾 <b>Государства Эрциона</b>\n\n"
    for country in countries:
        text += f"🏴 <b>{country.name}</b>"
        if country.owner_username:
            text += f" — @{country.owner_username}"
        short_desc = country.description[:80] + "…" if len(country.description) > 80 else country.description
        text += f"\n<i>{short_desc}</i>\n\n"

    username = await get_bot_username(bot)
    builder = InlineKeyboardBuilder()
    if username:
        builder.row(InlineKeyboardButton(text="📖 Подробнее в ЛС", url=f"https://t.me/{username}"))
        builder.row(InlineKeyboardButton(text="🏴 Основать страну", url=f"https://t.me/{username}"))

    await message.answer(text[:4096], reply_markup=builder.as_markup() if username else None)


# ─── /start в группе ──────────────────────────────────────────────────────────

@router.message(Command("start"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_start_group(message: Message, bot: Bot):
    username = await get_bot_username(bot)
    text = (
        "⚔️ <b>Эрцион III Season</b>\n\n"
        "Добро пожаловать! Используй команды для получения информации о мире.\n\n"
        "/races — расы\n"
        "/countries — страны\n"
        "/rules — правила\n"
        "/news — нововведения\n"
        "/start_conditions — стартовые условия\n"
        "/minerals — ресурсы\n"
        "/help — список команд\n\n"
        "📬 Регистрация рас и стран — только в личных сообщениях бота."
    )
    builder = InlineKeyboardBuilder()
    if username:
        builder.row(InlineKeyboardButton(text="✉️ Открыть бота в ЛС", url=f"https://t.me/{username}"))
    await message.answer(text, reply_markup=builder.as_markup() if username else None)
