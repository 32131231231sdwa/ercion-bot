import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from keyboards.menus import battle_menu_keyboard, battle_ai_keyboard, back_to_menu, cancel_keyboard
from utils.helpers import is_admin
from utils.ai_battle import generate_battle_outcomes_ai, generate_battle_random

logger = logging.getLogger(__name__)
router = Router()


class BattleForm(StatesGroup):
    force_a = State()
    force_b = State()
    awaiting_outcome = State()


@router.callback_query(F.data == "battle_menu")
async def battle_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Раздел боя доступен только администраторам.", show_alert=True)
        return
    text = "⚔️ <b>Боевая механика Эрциона</b>\n\nЗдесь ты можешь провести сражение между двумя силами. ИИ-летописец опишет 10 возможных исходов и выберет произошедший."
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=battle_menu_keyboard(), parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=battle_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "battle_new")
async def battle_new(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(BattleForm.force_a)
    text = "⚔️ <b>Новое сражение</b>\n\nВведи название <b>Силы А</b>:\n\n<i>Пример: «Армия Северного Альянса», «Орды клана Кровавого Молота»</i>"
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=cancel_keyboard(), parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(BattleForm.force_a)
async def battle_force_a(message: Message, state: FSMContext):
    await state.update_data(force_a=message.text.strip())
    await state.set_state(BattleForm.force_b)
    await message.answer(
        f"⚔️ <b>Сила А:</b> {message.text.strip()}\n\nТеперь введи название <b>Силы Б</b>:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(BattleForm.force_b)
async def battle_force_b(message: Message, state: FSMContext):
    data = await state.get_data()
    force_b = message.text.strip()
    await state.update_data(force_b=force_b)
    await state.set_state(BattleForm.awaiting_outcome)
    text = (
        f"⚔️ <b>Битва:</b> {data['force_a']} vs {force_b}\n\n"
        f"Как определить исход сражения?"
    )
    await message.answer(text, reply_markup=battle_ai_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "battle_ai", BattleForm.awaiting_outcome)
async def battle_ai_outcome(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    data = await state.get_data()
    await state.clear()
    force_a = data.get("force_a", "Сила А")
    force_b = data.get("force_b", "Сила Б")
    await callback.answer("Летописец работает...", show_alert=False)
    if callback.message.photo:
        await callback.message.edit_caption(
            caption="🤖 <i>Летописец изучает расстановку сил...</i>",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "🤖 <i>Летописец изучает расстановку сил...</i>",
            parse_mode="HTML"
        )
    ai_result = await generate_battle_outcomes_ai(force_a, force_b)
    if ai_result:
        text = f"⚔️ <b>Битва: {force_a} vs {force_b}</b>\n\n🤖 <b>Летописец Эрциона:</b>\n\n{ai_result}"
    else:
        text = generate_battle_random(force_a, force_b)
        text += "\n\n<i>(ИИ недоступен — использован случайный исход)</i>"
    if callback.message.photo:
        await callback.message.edit_caption(caption=text[:1024], reply_markup=back_to_menu(), parse_mode="HTML")
    else:
        if len(text) > 4096:
            await callback.message.edit_text(text[:4096], reply_markup=back_to_menu(), parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=back_to_menu(), parse_mode="HTML")


@router.callback_query(F.data == "battle_random", BattleForm.awaiting_outcome)
async def battle_random_outcome(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    data = await state.get_data()
    await state.clear()
    force_a = data.get("force_a", "Сила А")
    force_b = data.get("force_b", "Сила Б")
    text = generate_battle_random(force_a, force_b)
    await callback.answer()
    if callback.message.photo:
        await callback.message.edit_caption(caption=text[:1024], reply_markup=back_to_menu(), parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=back_to_menu(), parse_mode="HTML")
