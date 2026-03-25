from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Config:
    BOT_TOKEN: str
    ADMIN_ID: int
    SUBSCRIBE_CHANNEL_ID: int
    SUBSCRIBE_CHANNEL_LINK: str
    SCHEDULE_CHANNEL_ID: int
    DATABASE_PATH: str = "bot.db"
    TIMEZONE: str = "Europe/Moscow"


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id = os.getenv("ADMIN_ID", "").strip()
    subscribe_channel_id = os.getenv("SUBSCRIBE_CHANNEL_ID", "").strip()
    subscribe_channel_link = os.getenv("SUBSCRIBE_CHANNEL_LINK", "").strip()
    schedule_channel_id = os.getenv("SCHEDULE_CHANNEL_ID", "").strip()

    if not bot_token:
        raise ValueError("Не найден BOT_TOKEN в .env")
    if not admin_id:
        raise ValueError("Не найден ADMIN_ID в .env")
    if not subscribe_channel_id:
        raise ValueError("Не найден SUBSCRIBE_CHANNEL_ID в .env")
    if not subscribe_channel_link:
        raise ValueError("Не найден SUBSCRIBE_CHANNEL_LINK в .env")
    if not schedule_channel_id:
        raise ValueError("Не найден SCHEDULE_CHANNEL_ID в .env")

    return Config(
        BOT_TOKEN=bot_token,
        ADMIN_ID=int(admin_id),
        SUBSCRIBE_CHANNEL_ID=int(subscribe_channel_id),
        SUBSCRIBE_CHANNEL_LINK=subscribe_channel_link,
        SCHEDULE_CHANNEL_ID=int(schedule_channel_id),
        DATABASE_PATH=os.getenv("DATABASE_PATH", "bot.db"),
        TIMEZONE=os.getenv("TIMEZONE", "Europe/Moscow"),
    )
