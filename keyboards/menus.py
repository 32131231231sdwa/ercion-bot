from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔥 Правила", callback_data="rules"),
        InlineKeyboardButton(text="⚡ Нововведения", callback_data="changelog"),
    )
    builder.row(
        InlineKeyboardButton(text="🏰 Стартовые условия", callback_data="start_conditions"),
        InlineKeyboardButton(text="⛏ Ископаемые", callback_data="minerals"),
    )
    builder.row(
        InlineKeyboardButton(text="🧝 Расы", callback_data="races:0"),
        InlineKeyboardButton(text="🗾 Страны", callback_data="countries:0"),
    )
    builder.row(InlineKeyboardButton(text="🎌 Моя страна", callback_data="my_country"))
    builder.row(
        InlineKeyboardButton(text="✍ Зарегистрировать расу", callback_data="race_register"),
    )
    builder.row(
        InlineKeyboardButton(text="🏴 Основать страну", callback_data="country_register"),
    )
    if is_admin:
        builder.row(InlineKeyboardButton(text="⚔️ Бой", callback_data="battle_menu"))
        builder.row(InlineKeyboardButton(text="🛠 Админ-панель", callback_data="admin_panel"))
    builder.row(InlineKeyboardButton(text="❓ Помощь", callback_data="help"))
    return builder.as_markup()


def subscribe_keyboard(channel: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📜 Подписаться на канал", url=f"https://t.me/{channel.lstrip('@')}"))
    builder.row(InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub"))
    return builder.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="↩ Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def races_keyboard(races: list, page: int, total_pages: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for race in races:
        label = f"{'👑 ' if not race.is_custom else '🧬 '}{race.name}"
        builder.row(InlineKeyboardButton(text=label, callback_data=f"race_view:{race.id}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"races:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"races:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="↩ Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def race_detail_keyboard(race_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"race_edit:{race_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"race_delete:{race_id}"),
        )
    builder.row(InlineKeyboardButton(text="↩ К расам", callback_data="races:0"))
    return builder.as_markup()


def countries_keyboard(countries: list, page: int, total_pages: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in countries:
        builder.row(InlineKeyboardButton(text=f"🏴 {country.name}", callback_data=f"country_view:{country.id}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"countries:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"countries:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="↩ Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def country_detail_keyboard(country_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"country_edit:{country_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"country_delete:{country_id}"),
        )
    builder.row(InlineKeyboardButton(text="↩ К странам", callback_data="countries:0"))
    return builder.as_markup()


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.row(
        InlineKeyboardButton(text="🧬 Заявки на расы", callback_data="admin_races_pending:0"),
        InlineKeyboardButton(text="🏴 Заявки на страны", callback_data="admin_countries_pending:0"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Все расы", callback_data="admin_all_races:0"),
        InlineKeyboardButton(text="🗺 Все страны", callback_data="admin_all_countries:0"),
    )
    builder.row(InlineKeyboardButton(text="📜 Журнал действий", callback_data="admin_logs:0"))
    builder.row(InlineKeyboardButton(text="📥 Экспорт БД в CSV", callback_data="admin_export"))
    builder.row(
        InlineKeyboardButton(text="✏️ Правила", callback_data="edit_rules"),
        InlineKeyboardButton(text="✏️ Нововведения", callback_data="edit_changelog"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Стартовые условия", callback_data="edit_start_conditions"),
        InlineKeyboardButton(text="✏️ Ископаемые", callback_data="edit_minerals"),
    )
    builder.row(InlineKeyboardButton(text="✏️ Помощь", callback_data="edit_help"))
    builder.row(InlineKeyboardButton(text="↩ Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def approve_reject_keyboard(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Принять", callback_data=f"approve:{item_type}:{item_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{item_type}:{item_id}"),
    )
    return builder.as_markup()


def pending_list_keyboard(items: list, item_type: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.row(InlineKeyboardButton(
            text=f"📌 {item.name}",
            callback_data=f"admin_view:{item_type}:{item.id}"
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"admin_{item_type}s_pending:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"admin_{item_type}s_pending:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="↩ Админ-панель", callback_data="admin_panel"))
    return builder.as_markup()


def admin_all_races_keyboard(races: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for race in races:
        icon = "✅" if race.is_approved else ("⏳" if race.status == "pending" else "❌")
        builder.row(InlineKeyboardButton(text=f"{icon} {race.name}", callback_data=f"admin_view:race:{race.id}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"admin_all_races:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"admin_all_races:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="↩ Админ-панель", callback_data="admin_panel"))
    return builder.as_markup()


def admin_all_countries_keyboard(countries: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in countries:
        icon = "✅" if country.is_approved else ("⏳" if country.status == "pending" else "❌")
        builder.row(InlineKeyboardButton(text=f"{icon} {country.name}", callback_data=f"admin_view:country:{country.id}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"admin_all_countries:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"admin_all_countries:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="↩ Админ-панель", callback_data="admin_panel"))
    return builder.as_markup()


def admin_item_manage_keyboard(item_type: str, item_id: int, is_approved: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_approved:
        builder.row(
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve:{item_type}:{item_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{item_type}:{item_id}"),
        )
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"{item_type}_edit:{item_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"{item_type}_delete:{item_id}"),
    )
    back = "admin_races_pending:0" if item_type == "race" else "admin_countries_pending:0"
    builder.row(InlineKeyboardButton(text="↩ Назад", callback_data=back))
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_form"))
    return builder.as_markup()


def skip_photo_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏭ Пропустить фото", callback_data="skip_photo"))
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_form"))
    return builder.as_markup()


def battle_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚔️ Новый бой", callback_data="battle_new"))
    builder.row(InlineKeyboardButton(text="↩ Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def battle_ai_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🤖 Запросить ИИ", callback_data="battle_ai"))
    builder.row(InlineKeyboardButton(text="🎲 Случайный исход", callback_data="battle_random"))
    builder.row(InlineKeyboardButton(text="↩ Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def confirm_delete_keyboard(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete:{item_type}:{item_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="admin_panel"),
    )
    return builder.as_markup()
