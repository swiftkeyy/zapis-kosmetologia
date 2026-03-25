from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database.db import Database
from handlers.admin import router as admin_router
from handlers.booking import router as booking_router
from handlers.start import router as start_router
from services.scheduler import ReminderScheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    config = load_config()

    db = Database(config.DATABASE_PATH)
    await db.init()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    scheduler = ReminderScheduler(bot=bot, db=db, timezone=config.TIMEZONE)
    scheduler.start()
    await scheduler.restore_jobs()

    dp["config"] = config
    dp["db"] = db
    dp["scheduler"] = scheduler

    # Порядок важен: сначала админские роутеры, затем пользовательские.
    dp.include_router(admin_router)
    dp.include_router(booking_router)
    dp.include_router(start_router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
