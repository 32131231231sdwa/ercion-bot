import csv
import io
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy import select, func

from models.database import (
    async_session_maker, Race, Country, User, ActionLog, log_action,
    get_setting, set_setting
)
from keyboards.menus import (
    admin_panel_keyboard, pending_list_keyboard, admin_item_manage_keyboard,
    approve_reject_keyboard, back_to_menu, admin_all_races_keyboard,
    admin_all_countries_keyboard
)
from utils.helpers import (
    is_admin, paginate, format_pending_race, format_pending_country,
    format_race_text, format_country_text, safe_edit
)

logger = logging.getLogger(__name__)
router = Router()


class EditTextState(StatesGroup):
    entering = State()


# ─── Панель ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await safe_edit(callback.message, "🛠 <b>Админ-панель Эрциона</b>\n\nВыбери действие:", admin_panel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    async with async_session_maker() as session:
        user_count = await session.scalar(select(func.count(User.id)))
        race_pending = await session.scalar(select(func.count(Race.id)).where(Race.status == "pending"))
        race_approved = await session.scalar(select(func.count(Race.id)).where(Race.is_approved == True, Race.is_custom == True))
        country_pending = await session.scalar(select(func.count(Country.id)).where(Country.status == "pending"))
        country_approved = await session.scalar(select(func.count(Country.id)).where(Country.is_approved == True))
    text = (
        f"📊 <b>Статистика Эрциона</b>\n\n"
        f"👥 Пользователей: <b>{user_count}</b>\n\n"
        f"🧬 Расы:\n  ⏳ Ожидают: <b>{race_pending}</b>\n  ✅ Одобрено: <b>{race_approved}</b>\n\n"
        f"🏴 Страны:\n  ⏳ Ожидают: <b>{country_pending}</b>\n  ✅ Одобрено: <b>{country_approved}</b>"
    )
    await safe_edit(callback.message, text, back_to_menu())
    await callback.answer()


# ─── Редактирование текстов ───────────────────────────────────────────────────

EDIT_TEXT_KEYS = {
    "edit_rules": ("rules", "🔥 Правила"),
    "edit_changelog": ("changelog", "⚡ Нововведения"),
    "edit_start_conditions": ("start_conditions", "🏰 Стартовые условия"),
    "edit_minerals": ("minerals", "⛏ Ископаемые"),
    "edit_help": ("help", "❓ Помощь"),
}


@router.callback_query(F.data.in_(EDIT_TEXT_KEYS.keys()))
async def edit_text_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    key, label = EDIT_TEXT_KEYS[callback.data]
    current = await get_setting(key)
    await state.update_data(edit_text_key=key)
    await state.set_state(EditTextState.entering)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit"))
    preview = current[:300] + "..." if len(current) > 300 else current
    await safe_edit(
        callback.message,
        f"✏️ <b>Редактирование: {label}</b>\n\n<b>Текущий текст:</b>\n<code>{preview}</code>\n\n"
        f"Отправь новый текст. Поддерживается HTML-разметка (<b>жирный</b>, <i>курсив</i>, <code>код</code>).",
        builder.as_markup()
    )
    await callback.answer()


@router.message(EditTextState.entering)
async def edit_text_save(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("edit_text_key")
    await state.clear()
    if not key:
        await message.answer("Ошибка: ключ не найден.", reply_markup=back_to_menu())
        return
    await set_setting(key, message.text.strip())
    labels = {v[0]: v[1] for v in EDIT_TEXT_KEYS.values()}
    await log_action(message.from_user.id, message.from_user.username or "", f"edit_{key}", "setting", None, labels.get(key, key))
    await message.answer(f"✅ <b>{labels.get(key, key)}</b> обновлено.", reply_markup=back_to_menu(), parse_mode="HTML")


# ─── Заявки на расы ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_races_pending:"))
async def admin_races_pending(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    page = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        result = await session.execute(select(Race).where(Race.status == "pending").order_by(Race.created_at))
        races = result.scalars().all()
    items, page, total_pages = paginate(races, page)
    if not items:
        await safe_edit(callback.message, "⏳ Нет заявок на расы.", back_to_menu())
    else:
        await safe_edit(
            callback.message,
            f"🧬 <b>Заявки на расы</b> ({len(races)} шт.)\n\nВыбери заявку:",
            pending_list_keyboard(items, "race", page, total_pages)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_countries_pending:"))
async def admin_countries_pending(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    page = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        result = await session.execute(select(Country).where(Country.status == "pending").order_by(Country.created_at))
        countries = result.scalars().all()
    items, page, total_pages = paginate(countries, page)
    if not items:
        await safe_edit(callback.message, "⏳ Нет заявок на страны.", back_to_menu())
    else:
        await safe_edit(
            callback.message,
            f"🏴 <b>Заявки на страны</b> ({len(countries)} шт.)\n\nВыбери заявку:",
            pending_list_keyboard(items, "country", page, total_pages)
        )
    await callback.answer()


# ─── Все расы / все страны ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_all_races:"))
async def admin_all_races(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    page = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        result = await session.execute(select(Race).order_by(Race.is_custom, Race.name))
        races = result.scalars().all()
    items, page, total_pages = paginate(races, page)
    await safe_edit(callback.message, f"📋 <b>Все расы</b> ({len(races)} шт.):", admin_all_races_keyboard(items, page, total_pages))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_all_countries:"))
async def admin_all_countries(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    page = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        result = await session.execute(select(Country).order_by(Country.name))
        countries = result.scalars().all()
    items, page, total_pages = paginate(countries, page)
    await safe_edit(callback.message, f"🗺 <b>Все страны</b> ({len(countries)} шт.):", admin_all_countries_keyboard(items, page, total_pages))
    await callback.answer()


# ─── Просмотр конкретной заявки ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_view:"))
async def admin_view_item(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, item_type, item_id = callback.data.split(":")
    item_id = int(item_id)
    async with async_session_maker() as session:
        if item_type == "race":
            item = await session.get(Race, item_id)
            text = format_pending_race(item) if item else "Не найдено."
            is_approved = item.is_approved if item else False
            photo = item.photo_file_id if item else None
        else:
            item = await session.get(Country, item_id)
            text = format_pending_country(item) if item else "Не найдено."
            is_approved = item.is_approved if item else False
            photo = item.photo_file_id if item else None
    if not item:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    kb = admin_item_manage_keyboard(item_type, item_id, is_approved)
    if photo:
        try:
            await callback.message.delete()
            await callback.message.answer_photo(photo=photo, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
        except Exception:
            await safe_edit(callback.message, text, kb)
    else:
        await safe_edit(callback.message, text, kb)
    await callback.answer()


# ─── Одобрение / отклонение ───────────────────────────────────────────────────

async def _notify_other_admins(bot: Bot, actor_id: int, actor_username: str, text: str):
    """Отправить уведомление всем остальным админам (кроме того, кто принял решение)."""
    from utils.helpers import ADMIN_IDS
    actor_label = f"@{actor_username}" if actor_username else str(actor_id)
    for admin_id in ADMIN_IDS:
        if admin_id == actor_id:
            continue
        try:
            await bot.send_message(admin_id, f"{text}\n\n<i>Решение принял: {actor_label}</i>", parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")


@router.callback_query(F.data.startswith("approve:"))
async def approve_item(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, item_type, item_id = callback.data.split(":")
    item_id = int(item_id)

    async with async_session_maker() as session:
        if item_type == "race":
            item = await session.get(Race, item_id)
        else:
            item = await session.get(Country, item_id)

        if not item:
            await callback.answer("Запись не найдена.", show_alert=True)
            return

        # Уже обработано другим админом
        if item.status != "pending":
            status_label = "одобрено" if item.status == "approved" else "отклонено"
            await callback.answer(f"Эта заявка уже {status_label}.", show_alert=True)
            await safe_edit(
                callback.message,
                f"{'✅' if item.status == 'approved' else '❌'} <b>{item.name}</b> — уже {status_label}.",
                back_to_menu()
            )
            return

        item.is_approved = True
        item.status = "approved"
        await session.commit()
        name = item.name
        owner_id = item.created_by if item_type == "race" else item.owner_id

    await log_action(callback.from_user.id, callback.from_user.username or "", f"approve_{item_type}", item_type, item_id, name)
    await callback.answer("✅ Одобрено!")
    await safe_edit(callback.message, f"✅ <b>{name}</b> — одобрено и добавлено в список.", back_to_menu())

    type_ru = "раса" if item_type == "race" else "страна"

    # Уведомить игрока
    if owner_id:
        try:
            await bot.send_message(owner_id, f"✅ Твоя заявка <b>«{name}»</b> ({type_ru}) одобрена!", parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Could not notify user {owner_id}: {e}")

    # Уведомить остальных админов
    await _notify_other_admins(
        bot, callback.from_user.id, callback.from_user.username or "",
        f"✅ Заявка <b>«{name}»</b> ({type_ru}) — <b>одобрена</b>"
    )


@router.callback_query(F.data.startswith("reject:"))
async def reject_item(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, item_type, item_id = callback.data.split(":")
    item_id = int(item_id)

    async with async_session_maker() as session:
        if item_type == "race":
            item = await session.get(Race, item_id)
        else:
            item = await session.get(Country, item_id)

        if not item:
            await callback.answer("Запись не найдена.", show_alert=True)
            return

        # Уже обработано другим админом
        if item.status != "pending":
            status_label = "одобрено" if item.status == "approved" else "отклонено"
            await callback.answer(f"Эта заявка уже {status_label}.", show_alert=True)
            await safe_edit(
                callback.message,
                f"{'✅' if item.status == 'approved' else '❌'} <b>{item.name}</b> — уже {status_label}.",
                back_to_menu()
            )
            return

        item.status = "rejected"
        await session.commit()
        name = item.name
        owner_id = item.created_by if item_type == "race" else item.owner_id

    await log_action(callback.from_user.id, callback.from_user.username or "", f"reject_{item_type}", item_type, item_id, name)
    await callback.answer("❌ Отклонено.")
    await safe_edit(callback.message, f"❌ <b>{name}</b> — отклонено.", back_to_menu())

    type_ru = "раса" if item_type == "race" else "страна"

    # Уведомить игрока
    if owner_id:
        try:
            await bot.send_message(owner_id, f"❌ Заявка <b>«{name}»</b> ({type_ru}) отклонена.", parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Could not notify user {owner_id}: {e}")

    # Уведомить остальных админов
    await _notify_other_admins(
        bot, callback.from_user.id, callback.from_user.username or "",
        f"❌ Заявка <b>«{name}»</b> ({type_ru}) — <b>отклонена</b>"
    )
    if owner_id:
        try:
            type_ru = "раса" if item_type == "race" else "страна"
            await bot.send_message(owner_id, f"❌ Заявка <b>«{name}»</b> ({type_ru}) отклонена.", parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Could not notify user {owner_id}: {e}")


# ─── Журнал ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_logs:"))
async def admin_logs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    page = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        result = await session.execute(select(ActionLog).order_by(ActionLog.created_at.desc()))
        logs = result.scalars().all()
    if not logs:
        await safe_edit(callback.message, "📜 Журнал действий пуст.", back_to_menu())
        await callback.answer()
        return
    items, page, total_pages = paginate(logs, page, page_size=10)
    text = "📜 <b>Журнал действий</b>\n\n"
    for log in items:
        dt = log.created_at.strftime("%d.%m %H:%M") if log.created_at else "?"
        admin_name = f"@{log.admin_username}" if log.admin_username else str(log.admin_id)
        target = f" → {log.target_name}" if log.target_name else ""
        text += f"<code>{dt}</code> {admin_name}: <b>{log.action}</b>{target}\n"
    builder = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"admin_logs:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"admin_logs:{page+1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="↩ Админ-панель", callback_data="admin_panel"))
    await safe_edit(callback.message, text, builder.as_markup())
    await callback.answer()


# ─── Экспорт ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_export")
async def admin_export(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer("Генерирую CSV...")
    async with async_session_maker() as session:
        races = (await session.execute(select(Race))).scalars().all()
        countries = (await session.execute(select(Country))).scalars().all()
        users = (await session.execute(select(User))).scalars().all()
        logs = (await session.execute(select(ActionLog).order_by(ActionLog.created_at.desc()).limit(500))).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["=== ПОЛЬЗОВАТЕЛИ ==="])
    writer.writerow(["ID", "Telegram ID", "Username", "Имя", "Дата"])
    for u in users:
        writer.writerow([u.id, u.telegram_id, u.username, u.first_name,
                         u.joined_at.strftime("%d.%m.%Y") if u.joined_at else ""])

    writer.writerow([])
    writer.writerow(["=== РАСЫ ==="])
    writer.writerow(["ID", "Название", "Кастомная", "Одобрена", "Статус", "Создал", "Дата"])
    for r in races:
        writer.writerow([r.id, r.name, r.is_custom, r.is_approved, r.status,
                         r.created_by_username, r.created_at.strftime("%d.%m.%Y") if r.created_at else ""])

    writer.writerow([])
    writer.writerow(["=== СТРАНЫ ==="])
    writer.writerow(["ID", "Название", "Правитель", "Одобрена", "Статус", "Дата"])
    for c in countries:
        writer.writerow([c.id, c.name, c.owner_username, c.is_approved, c.status,
                         c.created_at.strftime("%d.%m.%Y") if c.created_at else ""])

    writer.writerow([])
    writer.writerow(["=== ЖУРНАЛ ДЕЙСТВИЙ ==="])
    writer.writerow(["ID", "Администратор", "Действие", "Тип", "Цель", "Дата"])
    for log in logs:
        writer.writerow([log.id, log.admin_username, log.action, log.target_type,
                         log.target_name, log.created_at.strftime("%d.%m.%Y %H:%M") if log.created_at else ""])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    filename = f"ercion_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file = BufferedInputFile(csv_bytes, filename=filename)
    await callback.message.answer_document(file, caption="📥 Экспорт базы данных Эрциона")
