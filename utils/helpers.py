import os
import logging
from typing import Optional
from aiogram.types import Message, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

ADMIN_IDS_RAW = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = set()
for _id in ADMIN_IDS_RAW.split(","):
    _id = _id.strip()
    if _id.isdigit():
        ADMIN_IDS.add(int(_id))

CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
ADMIN_NOTIFY_USERNAME = os.environ.get("ADMIN_NOTIFY_USERNAME", "@KrasnayaArmia")

PAGE_SIZE = 8
CAPTION_LIMIT = 1024


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def paginate(items: list, page: int, page_size: int = PAGE_SIZE):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = start + page_size
    return items[start:end], page, total_pages


async def safe_edit(message: Message, text: str,
                    reply_markup: InlineKeyboardMarkup = None,
                    parse_mode: str = "HTML"):
    """Универсальное редактирование: caption для фото, text — для текстовых."""
    try:
        if message.photo or message.document or message.sticker:
            caption = text[:CAPTION_LIMIT]
            await message.edit_caption(caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.edit_text(text[:4096], reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.debug(f"safe_edit failed ({e}), falling back to delete+send")
        try:
            await message.delete()
        except Exception:
            pass
        try:
            await message.answer(text[:4096], reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e2:
            logger.warning(f"safe_edit fallback also failed: {e2}")


def format_race_text(race) -> str:
    kind = "👑 Встроенная" if not race.is_custom else "🧬 Кастомная"
    text = f"🧝 <b>{race.name}</b>\n\n"
    text += f"<i>{race.description}</i>\n\n"
    if race.features:
        text += f"⚡ <b>Особенности:</b> {race.features}\n"
    text += f"\n{kind}"
    if race.created_by_username:
        text += f"\n✍ Создана: @{race.created_by_username}"
    return text


def format_country_text(country) -> str:
    text = f"🏴 <b>{country.name}</b>\n\n"
    text += f"<i>{country.description}</i>\n"
    if country.owner_username:
        text += f"\n👤 Правитель: @{country.owner_username}"
    return text


def format_pending_race(race) -> str:
    text = f"📬 <b>Заявка на расу: {race.name}</b>\n\n"
    text += f"<i>{race.description}</i>\n\n"
    if race.features:
        text += f"⚡ Особенности: {race.features}\n"
    if race.created_by_username:
        text += f"\n✍ Подал: @{race.created_by_username}"
    return text


def format_pending_country(country) -> str:
    text = f"📬 <b>Заявка на страну: {country.name}</b>\n\n"
    text += f"<i>{country.description}</i>\n"
    if country.owner_username:
        text += f"\n👤 Правитель: @{country.owner_username}"
    return text
