import logging
import os
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from models.database import async_session_maker, Race, log_action
from keyboards.menus import (
    races_keyboard, race_detail_keyboard, cancel_keyboard,
    skip_photo_keyboard, back_to_menu, approve_reject_keyboard,
    confirm_delete_keyboard
)
from utils.helpers import is_admin, paginate, format_race_text, format_pending_race, ADMIN_IDS, safe_edit

logger = logging.getLogger(__name__)
router = Router()


class RaceRegistration(StatesGroup):
    name = State()
    description = State()
    features = State()
    photo = State()


class RaceEditState(StatesGroup):
    choosing_field = State()
    entering_value = State()


async def get_all_approved_races():
    from sqlalchemy import select
    async with async_session_maker() as session:
        result = await session.execute(
            select(Race).where(Race.is_approved == True).order_by(Race.is_custom, Race.name)
        )
        return result.scalars().all()


@router.callback_query(F.data.startswith("races:"))
async def races_list(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    all_races = await get_all_approved_races()
    races_page, page, total_pages = paginate(all_races, page)
    admin = is_admin(callback.from_user.id)
    text = "🧝 <b>Расы Эрциона</b>\n\n👑 — встроенные расы\n🧬 — кастомные расы\n\nВыбери расу:"
    kb = races_keyboard(races_page, page, total_pages, admin)
    await safe_edit(callback.message, text, kb)
    await callback.answer()


@router.callback_query(F.data.startswith("race_view:"))
async def race_view(callback: CallbackQuery, bot: Bot):
    race_id = int(callback.data.split(":")[1])
    admin = is_admin(callback.from_user.id)

    async with async_session_maker() as session:
        race = await session.get(Race, race_id)

    if not race:
        await callback.answer("Раса не найдена.", show_alert=True)
        return

    text = format_race_text(race)
    kb = race_detail_keyboard(race_id, admin)

    if race.photo_file_id:
        try:
            # Сначала отправляем фото, потом удаляем старое — безопаснее
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=race.photo_file_id,
                caption=text[:1024],
                reply_markup=kb,
                parse_mode="HTML"
            )
            await callback.message.delete()
        except Exception as e:
            logger.warning(f"race_view photo failed: {e}")
            await safe_edit(callback.message, text, kb)
    else:
        await safe_edit(callback.message, text, kb)
    await callback.answer()


@router.callback_query(F.data == "race_register")
async def race_register_start(callback: CallbackQuery, state: FSMContext):
    if callback.message.chat.type != "private":
        await callback.answer("Регистрация только в личных сообщениях бота.", show_alert=True)
        return
    await state.set_state(RaceRegistration.name)
    await safe_edit(callback.message, "🧬 <b>Регистрация новой расы</b>\n\nВведи <b>название</b> расы:", cancel_keyboard())
    await callback.answer()


@router.message(RaceRegistration.name)
async def race_name_input(message: Message, state: FSMContext):
    if len(message.text) > 50:
        await message.answer("Название слишком длинное (макс. 50 символов). Попробуй снова:", reply_markup=cancel_keyboard())
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(RaceRegistration.description)
    await message.answer("📜 Отлично! Теперь напиши <b>описание</b> расы:", reply_markup=cancel_keyboard(), parse_mode="HTML")


@router.message(RaceRegistration.description)
async def race_description_input(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(RaceRegistration.features)
    await message.answer("⚡ Укажи <b>особенности</b> расы (уникальные черты, способности):", reply_markup=cancel_keyboard(), parse_mode="HTML")


@router.message(RaceRegistration.features)
async def race_features_input(message: Message, state: FSMContext):
    await state.update_data(features=message.text.strip())
    await state.set_state(RaceRegistration.photo)
    await message.answer("🖼 Прикрепи <b>изображение</b> расы или пропусти этот шаг:", reply_markup=skip_photo_keyboard(), parse_mode="HTML")


@router.message(RaceRegistration.photo, F.photo)
async def race_photo_input(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await finish_race_registration(message, state, bot)


@router.callback_query(F.data == "skip_photo", RaceRegistration.photo)
async def race_skip_photo(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.update_data(photo_file_id=None)
    await finish_race_registration(callback.message, state, bot, user=callback.from_user)
    await callback.answer()


async def finish_race_registration(message: Message, state: FSMContext, bot: Bot, user=None):
    data = await state.get_data()
    await state.clear()
    if user is None:
        user = message.from_user

    photo_id = data.get("photo_file_id")

    async with async_session_maker() as session:
        race = Race(
            name=data["name"],
            description=data["description"],
            features=data.get("features"),
            photo_file_id=photo_id,
            is_custom=True,
            is_approved=False,
            status="pending",
            created_by=user.id,
            created_by_username=user.username or user.first_name,
        )
        session.add(race)
        await session.commit()
        race_id = race.id
        race_name = race.name
        race_desc = race.description
        race_features = race.features
        race_username = race.created_by_username

    await message.answer(f"✅ Заявка на расу <b>{race_name}</b> отправлена на рассмотрение!", parse_mode="HTML")

    notify_text = (
        f"📬 <b>Заявка на расу: {race_name}</b>\n\n"
        f"<i>{race_desc}</i>\n\n"
    )
    if race_features:
        notify_text += f"⚡ Особенности: {race_features}\n"
    if race_username:
        notify_text += f"\n✍ Подал: @{race_username}"

    kb = approve_reject_keyboard("race", race_id)

    for admin_id in ADMIN_IDS:
        try:
            if photo_id:
                await bot.send_photo(
                    admin_id,
                    photo=photo_id,
                    caption=notify_text[:1024],
                    reply_markup=kb,
                    parse_mode="HTML",
                    disable_notification=False,
                )
            else:
                await bot.send_message(
                    admin_id,
                    notify_text,
                    reply_markup=kb,
                    parse_mode="HTML",
                    disable_notification=False,
                )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")


@router.callback_query(F.data == "cancel_form")
async def cancel_form(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(callback.message, "❌ Действие отменено.", back_to_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("race_delete:"))
async def race_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    race_id = int(callback.data.split(":")[1])
    await safe_edit(callback.message, "🗑 Ты уверен, что хочешь удалить эту расу?", confirm_delete_keyboard("race", race_id))
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:race:"))
async def confirm_race_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    race_id = int(callback.data.split(":")[2])
    name = "?"
    async with async_session_maker() as session:
        race = await session.get(Race, race_id)
        if race:
            name = race.name
            await session.delete(race)
            await session.commit()
    await log_action(callback.from_user.id, callback.from_user.username or "", "delete_race", "race", race_id, name)
    await safe_edit(callback.message, f"🗑 Раса <b>{name}</b> удалена.", back_to_menu())
    await callback.answer("Удалено.")


@router.callback_query(F.data.startswith("race_edit:"))
async def race_edit_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    race_id = int(callback.data.split(":")[1])
    await state.update_data(edit_race_id=race_id)
    await state.set_state(RaceEditState.choosing_field)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📛 Название", callback_data=f"race_edit_field:{race_id}:name"))
    builder.row(InlineKeyboardButton(text="📜 Описание", callback_data=f"race_edit_field:{race_id}:description"))
    builder.row(InlineKeyboardButton(text="⚡ Особенности", callback_data=f"race_edit_field:{race_id}:features"))
    builder.row(InlineKeyboardButton(text="↩ Отмена", callback_data="cancel_edit"))
    await safe_edit(callback.message, "✏️ Что хочешь изменить?", builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("race_edit_field:"))
async def race_edit_field(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    race_id, field = int(parts[1]), parts[2]
    await state.update_data(edit_race_id=race_id, edit_field=field)
    await state.set_state(RaceEditState.entering_value)
    field_names = {"name": "название", "description": "описание", "features": "особенности"}
    await safe_edit(callback.message, f"✏️ Введи новое <b>{field_names.get(field, field)}</b>:", cancel_keyboard())
    await callback.answer()


@router.message(RaceEditState.entering_value)
async def race_edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    race_id, field = data["edit_race_id"], data["edit_field"]
    await state.clear()
    async with async_session_maker() as session:
        race = await session.get(Race, race_id)
        if race:
            setattr(race, field, message.text.strip())
            await session.commit()
            await log_action(message.from_user.id, message.from_user.username or "", f"edit_race_{field}", "race", race_id, race.name)
    await message.answer("✅ Изменения сохранены.", reply_markup=back_to_menu(), parse_mode="HTML")


@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(callback.message, "❌ Редактирование отменено.", back_to_menu())
    await callback.answer()
