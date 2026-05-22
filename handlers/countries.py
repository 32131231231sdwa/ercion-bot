import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy import select

from models.database import async_session_maker, Country, log_action
from keyboards.menus import (
    countries_keyboard, country_detail_keyboard, cancel_keyboard,
    skip_photo_keyboard, back_to_menu, approve_reject_keyboard,
    confirm_delete_keyboard
)
from utils.helpers import is_admin, paginate, format_country_text, format_pending_country, ADMIN_IDS, safe_edit

logger = logging.getLogger(__name__)
router = Router()


class CountryRegistration(StatesGroup):
    name = State()
    description = State()
    photo = State()


class CountryEditState(StatesGroup):
    choosing_field = State()
    entering_value = State()


async def get_approved_countries():
    async with async_session_maker() as session:
        result = await session.execute(
            select(Country).where(Country.is_approved == True).order_by(Country.name)
        )
        return result.scalars().all()


@router.callback_query(F.data.startswith("countries:"))
async def countries_list(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    all_countries = await get_approved_countries()
    countries_page, page, total_pages = paginate(all_countries, page)
    admin = is_admin(callback.from_user.id)
    text = "🗾 <b>Страны Эрциона</b>\n\nВыбери страну для просмотра:"
    kb = countries_keyboard(countries_page, page, total_pages, admin)
    await safe_edit(callback.message, text, kb)
    await callback.answer()


@router.callback_query(F.data.startswith("country_view:"))
async def country_view(callback: CallbackQuery, bot: Bot):
    country_id = int(callback.data.split(":")[1])
    admin = is_admin(callback.from_user.id)
    async with async_session_maker() as session:
        country = await session.get(Country, country_id)
    if not country:
        await callback.answer("Страна не найдена.", show_alert=True)
        return
    text = format_country_text(country)
    kb = country_detail_keyboard(country_id, admin)
    if country.photo_file_id:
        try:
            # Сначала отправляем, потом удаляем — безопаснее
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=country.photo_file_id,
                caption=text[:1024],
                reply_markup=kb,
                parse_mode="HTML"
            )
            await callback.message.delete()
        except Exception as e:
            logger.warning(f"country_view photo failed: {e}")
            await safe_edit(callback.message, text, kb)
    else:
        await safe_edit(callback.message, text, kb)
    await callback.answer()


@router.callback_query(F.data == "my_country")
async def my_country(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        result = await session.execute(
            select(Country).where(Country.owner_id == user_id, Country.is_approved == True)
        )
        countries = result.scalars().all()
    if not countries:
        await safe_edit(callback.message, "🏴 У тебя пока нет одобренных стран.\n\nОснуй страну, чтобы она появилась здесь!", back_to_menu())
        await callback.answer()
        return
    text = "🎌 <b>Твои страны:</b>\n\n"
    for c in countries:
        desc_preview = c.description[:80] + "..." if len(c.description) > 80 else c.description
        text += f"🏴 <b>{c.name}</b>\n{desc_preview}\n\n"
    await safe_edit(callback.message, text, back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "my_countries")
async def my_countries_filter(callback: CallbackQuery):
    await my_country(callback)


@router.callback_query(F.data == "country_register")
async def country_register_start(callback: CallbackQuery, state: FSMContext):
    if callback.message.chat.type != "private":
        await callback.answer("Регистрация только в личных сообщениях бота.", show_alert=True)
        return
    await state.set_state(CountryRegistration.name)
    await safe_edit(callback.message, "🏰 <b>Основание новой страны</b>\n\nВведи <b>название</b> своей страны:", cancel_keyboard())
    await callback.answer()


@router.message(CountryRegistration.name)
async def country_name_input(message: Message, state: FSMContext):
    if len(message.text) > 60:
        await message.answer("Название слишком длинное (макс. 60 символов).", reply_markup=cancel_keyboard())
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(CountryRegistration.description)
    await message.answer("📜 Опиши свою страну — её историю, народ, особенности:", reply_markup=cancel_keyboard(), parse_mode="HTML")


@router.message(CountryRegistration.description)
async def country_description_input(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(CountryRegistration.photo)
    await message.answer("🖼 Прикрепи <b>изображение</b> страны (герб, флаг, карту) или пропусти:", reply_markup=skip_photo_keyboard(), parse_mode="HTML")


@router.message(CountryRegistration.photo, F.photo)
async def country_photo_input(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await finish_country_registration(message, state, bot)


@router.callback_query(F.data == "skip_photo", CountryRegistration.photo)
async def country_skip_photo(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.update_data(photo_file_id=None)
    await finish_country_registration(callback.message, state, bot, user=callback.from_user)
    await callback.answer()


async def finish_country_registration(message: Message, state: FSMContext, bot: Bot, user=None):
    data = await state.get_data()
    await state.clear()
    if user is None:
        user = message.from_user

    photo_id = data.get("photo_file_id")

    async with async_session_maker() as session:
        country = Country(
            name=data["name"],
            description=data["description"],
            photo_file_id=photo_id,
            owner_id=user.id,
            owner_username=user.username or user.first_name,
            is_approved=False,
            status="pending",
        )
        session.add(country)
        await session.commit()
        country_id = country.id
        country_name = country.name
        country_desc = country.description
        country_username = country.owner_username

    await message.answer(f"✅ Заявка на страну <b>{country_name}</b> отправлена на рассмотрение!", parse_mode="HTML")

    notify_text = (
        f"📬 <b>Заявка на страну: {country_name}</b>\n\n"
        f"<i>{country_desc}</i>\n"
    )
    if country_username:
        notify_text += f"\n👤 Правитель: @{country_username}"

    kb = approve_reject_keyboard("country", country_id)

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


@router.callback_query(F.data.startswith("country_delete:"))
async def country_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    country_id = int(callback.data.split(":")[1])
    await safe_edit(callback.message, "🗑 Ты уверен, что хочешь удалить эту страну?", confirm_delete_keyboard("country", country_id))
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:country:"))
async def confirm_country_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    country_id = int(callback.data.split(":")[2])
    name = "?"
    async with async_session_maker() as session:
        country = await session.get(Country, country_id)
        if country:
            name = country.name
            await session.delete(country)
            await session.commit()
    await log_action(callback.from_user.id, callback.from_user.username or "", "delete_country", "country", country_id, name)
    await safe_edit(callback.message, f"🗑 Страна <b>{name}</b> удалена.", back_to_menu())
    await callback.answer("Удалено.")


@router.callback_query(F.data.startswith("country_edit:"))
async def country_edit_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    country_id = int(callback.data.split(":")[1])
    await state.update_data(edit_country_id=country_id)
    await state.set_state(CountryEditState.choosing_field)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📛 Название", callback_data=f"country_edit_field:{country_id}:name"))
    builder.row(InlineKeyboardButton(text="📜 Описание", callback_data=f"country_edit_field:{country_id}:description"))
    builder.row(InlineKeyboardButton(text="↩ Отмена", callback_data="cancel_edit"))
    await safe_edit(callback.message, "✏️ Что хочешь изменить?", builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("country_edit_field:"))
async def country_edit_field(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    country_id, field = int(parts[1]), parts[2]
    await state.update_data(edit_country_id=country_id, edit_field=field)
    await state.set_state(CountryEditState.entering_value)
    field_names = {"name": "название", "description": "описание"}
    await safe_edit(callback.message, f"✏️ Введи новое <b>{field_names.get(field, field)}</b>:", cancel_keyboard())
    await callback.answer()


@router.message(CountryEditState.entering_value)
async def country_edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    country_id, field = data["edit_country_id"], data["edit_field"]
    await state.clear()
    async with async_session_maker() as session:
        country = await session.get(Country, country_id)
        if country:
            setattr(country, field, message.text.strip())
            await session.commit()
            await log_action(message.from_user.id, message.from_user.username or "", f"edit_country_{field}", "country", country_id, country.name)
    await message.answer("✅ Изменения сохранены.", reply_markup=back_to_menu(), parse_mode="HTML")
