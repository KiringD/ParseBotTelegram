import asyncio

from aiogram.utils import executor
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.bot.api import TelegramAPIServer

from .database.aiohttp import start_aiohttp_server
from .database.methods import table_create
from .misc import TgKeys, tgparser, ConfigKeys
from .handlers import register_all_handlers
from .misc.util import start_all_scripts, start_post_calendar_service


# from refactor.database.models import register_models


async def __on_start_up(dp: Dispatcher) -> None:
    loop = asyncio.get_event_loop()
    table_create()
    start_all_scripts()
    register_all_handlers(dp)
    start_aiohttp_server()
    start_post_calendar_service()


    # register_models()

async def __on_shutdown(dp: Dispatcher):
    await dp.storage.close()
    await dp.storage.wait_closed()
    await tgparser.client.disconnect()


def start_bot():
    local_server = TelegramAPIServer.from_base(f'http://{ConfigKeys.telegram_host}:{ConfigKeys.telegram_port}')

    bot = Bot(token=TgKeys.TOKEN, server=local_server, parse_mode='HTML')
    dp = Dispatcher(bot, storage=MemoryStorage())

    executor.start_polling(dp, on_startup=__on_start_up, on_shutdown=__on_shutdown, skip_updates=True)
