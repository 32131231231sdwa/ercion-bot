import os
import logging
import urllib.parse as _urlparse
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Integer, String, Text,
    select, func
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///ercion.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL[len("postgresql://"):]

if DATABASE_URL.startswith("postgresql+asyncpg://"):
    _parsed = _urlparse.urlparse(DATABASE_URL)
    _qs = _urlparse.parse_qs(_parsed.query)
    _sslmode = (_qs.pop("sslmode", [None])[0] or "").lower()
    _new_query = _urlparse.urlencode({k: v[0] for k, v in _qs.items()})
    DATABASE_URL = _urlparse.urlunparse(_parsed._replace(query=_new_query))
    _SSL_CONNECT_ARGS = {"ssl": "require"} if _sslmode in ("require", "verify-ca", "verify-full") else {}
elif not DATABASE_URL.startswith("sqlite"):
    DATABASE_URL = "sqlite+aiosqlite:///ercion.db"
    _SSL_CONNECT_ARGS = {}
else:
    _SSL_CONNECT_ARGS = {}


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    is_subscribed = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)


class Race(Base):
    __tablename__ = "races"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    features = Column(Text, nullable=True)
    photo_file_id = Column(String(200), nullable=True)
    is_custom = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    status = Column(String(20), default="pending")
    created_by = Column(BigInteger, nullable=True)
    created_by_username = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    photo_file_id = Column(String(200), nullable=True)
    owner_id = Column(BigInteger, nullable=True)
    owner_username = Column(String(100), nullable=True)
    is_approved = Column(Boolean, default=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True)
    admin_id = Column(BigInteger, nullable=False)
    admin_username = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    target_name = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_SSL_CONNECT_ARGS)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_setting(key: str, default: str = "") -> str:
    async with async_session_maker() as session:
        row = await session.get(Setting, key)
        return row.value if row else default


async def set_setting(key: str, value: str):
    async with async_session_maker() as session:
        row = await session.get(Setting, key)
        if row:
            row.value = value
            row.updated_at = datetime.utcnow()
        else:
            row = Setting(key=key, value=value)
            session.add(row)
        await session.commit()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_builtin_races()
    await seed_default_settings()
    logger.info("Database initialized")


BUILTIN_RACES = [
    {
        "name": "Человек",
        "description": "Самая многочисленная раса Эрциона. Люди отличаются адаптивностью и целеустремлённостью. Среди них встречаются великие воины, маги и дипломаты.",
        "features": "Адаптивность · Быстрое обучение · Дипломатический дар",
    },
    {
        "name": "Эльф",
        "description": "Древние хранители лесов и магических знаний. Эльфы живут веками, накапливая мудрость и мастерство в искусствах и магии.",
        "features": "Долголетие · Острое зрение · Магическая предрасположенность",
    },
    {
        "name": "Дварф",
        "description": "Несгибаемые мастера гор. Дварфы — непревзойдённые кузнецы и горняки, хранящие традиции своих предков в подземных твердынях.",
        "features": "Стойкость · Кузнечное мастерство · Сопротивление ядам",
    },
    {
        "name": "Орк",
        "description": "Могучие воители степей. Орки чтят силу и честь, живут по законам клана и являются одними из самых грозных бойцов Эрциона.",
        "features": "Боевая ярость · Физическая мощь · Клановые связи",
    },
    {
        "name": "Нежить",
        "description": "Те, кого смерть не смогла удержать. Нежить существует на границе миров, обладая уникальными способностями, но лишённая тепла живых.",
        "features": "Бессмертие · Устойчивость к боли · Связь с тьмой",
    },
    {
        "name": "Тёмный эльф",
        "description": "Изгнанники светлых эльфов, освоившие тёмную магию глубин. Их история полна предательства и силы, выкованной в страдании.",
        "features": "Тёмная магия · Ночное зрение · Яды",
    },
    {
        "name": "Драконид",
        "description": "Потомки древних драконов, несущие в крови огонь и мощь. Редкая раса, каждый представитель которой — легенда сам по себе.",
        "features": "Дыхание огня · Чешуйчатая броня · Драконья кровь",
    },
    {
        "name": "Полурослик",
        "description": "Неприметные, но невероятно ловкие существа. Полурослики мастерски избегают опасности и обладают исключительной удачей.",
        "features": "Везение · Ловкость · Невидимость в толпе",
    },
]

DEFAULT_RULES = """🔥 <b>Правила Эрциона</b>

<b>Основные правила:</b>
1. Уважай других участников — личные оскорбления недопустимы
2. Все действия должны соответствовать сеттингу мира Эрцион
3. Решения администрации окончательны и не оспариваются
4. Запрещено использование магии высшего порядка без согласования с мастером

<b>Правила ролевой игры:</b>
1. Отыгрывай характер своего персонажа честно
2. Не смешивай ролевое и реальное общение
3. Смерть персонажа — это возможность, а не катастрофа
4. Уважай решения мастера по сюжету

<b>Боевые правила:</b>
1. Исходы сражений определяются системой или мастером
2. Нечестная игра карается баном персонажа
3. Подвиги фиксируются в летописи"""

DEFAULT_CHANGELOG = """⚡ <b>Свод нововведений — Сезон III</b>

<b>Достоверность:</b>
Все события должны опираться на реальную логику мира. Магия имеет ограничения, армии требуют снабжения, дипломатия важна как сила.

<b>Бои с ИИ:</b>
Система боёв теперь включает ИИ-летописца, который генерирует 10 вариантов исхода и выбирает произошедший. Результат обязателен к исполнению.

<b>Запреты:</b>
— Телепортация без артефакта перемещения
— Воскрешение без участия Жрецов Смерти
— Создание новых рас без одобрения администрации
— Захват столиц без объявления войны

<b>Новое:</b>
— Регистрация кастомных рас через бота
— Основание стран и управление ими
— Система заявок с уведомлениями"""

DEFAULT_START_CONDITIONS = """🏰 <b>Стартовые условия — Эрцион РП III Сезон</b>

<b>Население и земли:</b>
— Население страны при основании: до 100.000 душ
— Городское население: не более 10% от общего
— Сельское хозяйство — основа уклада, во многом натуральное

<b>Экономика:</b>
— Торговля ограниченная, но стабильная
— Монеты используются, однако бартер всё ещё распространён
— Ремесло развито умеренно, в городах действуют цехи
— Налоговая система неэффективна, казна нередко в дефиците
— Заёмные средства в ходу при нехватке средств

<b>Инфраструктура:</b>
— Дороги меж крупнейшими городами существуют
— Прочие земли связаны тропами и просёлками
— Ключевые мосты возведены, торговые маршруты функционируют

<b>Безопасность и управление:</b>
— Централизация слабая, регионы полуавтономны
— Коррупция высокая, власть опирается на личную преданность
— Регулярной армии нет — в ходу наёмные дружины
— До 10 укреплений (замки, башни, форты)

<b>Прочее:</b>
— Преступность достаточно активна
— Санитария оставляет желать лучшего
— Магия редка и ценится наравне с золотом"""

DEFAULT_HELP = """❓ <b>Помощь — Эрцион III Season</b>

<b>Команды бота (работают в группах и ЛС):</b>
/start — открыть главное меню (только в ЛС)
/help — список команд
/races — расы мира
/countries — государства мира
/rules — правила ролевой игры
/news — нововведения сезона
/start_conditions — стартовые условия
/minerals — полезные ископаемые

<b>Разделы меню (в ЛС бота):</b>
🔥 Правила — правила ролевой игры
⚡ Нововведения — изменения и обновления сезона
🏰 Стартовые условия — с чего начинает каждая страна
⛏ Ископаемые — справочник ресурсов мира
🧝 Расы — список всех рас Эрциона
🗾 Страны — одобренные государства мира
🎌 Моя страна — просмотр своих стран
✍ Зарегистрировать расу — подать заявку на новую расу
🏴 Основать страну — подать заявку на создание страны

<b>Регистрация:</b>
— Заявки принимаются только в личных сообщениях бота
— После подачи заявку рассматривает администрация
— При одобрении или отклонении придёт уведомление"""

DEFAULT_MINERALS = """⛏ <b>Полезные ископаемые Эрциона</b>

<b>Металлы:</b>
Магнетит · Гематит · Лимонит (железо)
Медь · Олово · Свинец · Цинк
Золото · Серебро · Электрум
Киноварь (ртуть) · Мифрил · Эрцион

<b>Горючие ресурсы:</b>
Каменный уголь · Торф · Битум · Нефть

<b>Соли и химические минералы:</b>
Каменная соль · Галит · Селитра
Сера · Квасцы · Нашатырь

<b>Строительные камни:</b>
Известняк · Мрамор · Гранит · Песчаник
Сланец · Базальт · Туф · Кремень
Мел · Глина · Каолин · Гипс · Алебастр

<b>Драгоценные и полудрагоценные камни:</b>
Алмаз · Сапфир · Рубин · Изумруд
Гранат · Аметист · Топаз · Бирюза
Агат · Оникс · Яшма · Сердолик
Горный хрусталь · Лазурит · Янтарь

<b>Пигменты:</b>
Охра · Умбра · Азурит · Малахит · Гематит"""


async def seed_builtin_races():
    async with async_session_maker() as session:
        result = await session.execute(select(Race).where(Race.is_custom == False))
        existing = result.scalars().all()
        if existing:
            return
        for race_data in BUILTIN_RACES:
            race = Race(
                name=race_data["name"],
                description=race_data["description"],
                features=race_data["features"],
                is_custom=False,
                is_approved=True,
                status="approved",
            )
            session.add(race)
        await session.commit()
        logger.info("Built-in races seeded")


async def seed_default_settings():
    async with async_session_maker() as session:
        for key, value in [
            ("rules", DEFAULT_RULES),
            ("changelog", DEFAULT_CHANGELOG),
            ("start_conditions", DEFAULT_START_CONDITIONS),
            ("minerals", DEFAULT_MINERALS),
            ("help", DEFAULT_HELP),
        ]:
            row = await session.get(Setting, key)
            if not row:
                session.add(Setting(key=key, value=value))
        await session.commit()


async def log_action(admin_id: int, admin_username: str, action: str,
                     target_type: str = None, target_id: int = None, target_name: str = None):
    async with async_session_maker() as session:
        log = ActionLog(
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
        )
        session.add(log)
        await session.commit()
