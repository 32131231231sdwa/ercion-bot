import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeAllGroupChats,
)

from models.database import init_db
from handlers import start, races, countries, admin, battle, groups

LOG_FILE = "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


COMMANDS_PRIVATE = [
    BotCommand(command="start",            description="Открыть главное меню"),
    BotCommand(command="help",             description="Помощь и список команд"),
    BotCommand(command="races",            description="Расы Эрциона"),
    BotCommand(command="countries",        description="Государства Эрциона"),
    BotCommand(command="rules",            description="Правила ролевой игры"),
    BotCommand(command="news",             description="Нововведения сезона"),
    BotCommand(command="start_conditions", description="Стартовые условия"),
    BotCommand(command="minerals",         description="Полезные ископаемые"),
]

COMMANDS_GROUP = [
    BotCommand(command="help",             description="Помощь и список команд"),
    BotCommand(command="races",            description="Расы Эрциона"),
    BotCommand(command="countries",        description="Государства Эрциона"),
    BotCommand(command="rules",            description="Правила ролевой игры"),
    BotCommand(command="news",             description="Нововведения сезона"),
    BotCommand(command="start_conditions", description="Стартовые условия"),
    BotCommand(command="minerals",         description="Полезные ископаемые"),
]


async def set_commands(bot: Bot):
    await bot.set_my_commands(COMMANDS_PRIVATE, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(COMMANDS_GROUP,   scope=BotCommandScopeAllGroupChats())
    logger.info("Bot commands registered")


async def main():
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.critical("BOT_TOKEN не задан. Завершение.")
        sys.exit(1)

    logger.info("Инициализация базы данных...")
    await init_db()

    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Групповые команды регистрируем первыми — /start в группе не
    # должен перехватываться обработчиком ЛС
    dp.include_router(groups.router)
    dp.include_router(start.router)
    dp.include_router(races.router)
    dp.include_router(countries.router)
    dp.include_router(admin.router)
    dp.include_router(battle.router)

    await set_commands(bot)

    logger.info("Бот Эрцион запускается...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
