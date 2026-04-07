from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Config:
    """Конфигурация приложения."""

    BOT_TOKEN: str
    ADMIN_ID: int
    CHANNEL_ID: int
    CHANNEL_LINK: str
    DATABASE_PATH: str = "bot.db"
    TIMEZONE: str = "Europe/Moscow"


def load_config() -> Config:
    """Загружает конфиг из .env."""

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id = os.getenv("ADMIN_ID", "").strip()
    channel_id = os.getenv("CHANNEL_ID", "").strip()
    channel_link = os.getenv("CHANNEL_LINK", "").strip()

    if not bot_token:
        raise ValueError("Не найден BOT_TOKEN в .env")

    if not admin_id:
        raise ValueError("Не найден ADMIN_ID в .env")

    if not channel_id:
        raise ValueError("Не найден CHANNEL_ID в .env")

    if not channel_link:
        raise ValueError("Не найден CHANNEL_LINK в .env")

    return Config(
        BOT_TOKEN=bot_token,
        ADMIN_ID=int(admin_id),
        CHANNEL_ID=int(channel_id),
        CHANNEL_LINK=channel_link,
        DATABASE_PATH=os.getenv("DATABASE_PATH", "bot.db"),
        TIMEZONE=os.getenv("TIMEZONE", "Europe/Moscow"),
    )
