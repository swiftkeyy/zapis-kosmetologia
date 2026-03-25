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
    ADMIN_IDS: list[int]
    CHANNEL_ID: int
    CHANNEL_LINK: str
    DATABASE_PATH: str = "bot.db"
    TIMEZONE: str = "Europe/Moscow"


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
    channel_id = os.getenv("CHANNEL_ID", "").strip()
    channel_link = os.getenv("CHANNEL_LINK", "").strip()

    if not bot_token:
        raise ValueError("Не найден BOT_TOKEN в .env")

    if not admin_ids_raw:
        raise ValueError("Не найден ADMIN_IDS в .env")

    if not channel_id:
        raise ValueError("Не найден CHANNEL_ID в .env")

    if not channel_link:
        raise ValueError("Не найден CHANNEL_LINK в .env")

    admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()]

    return Config(
        BOT_TOKEN=bot_token,
        ADMIN_IDS=admin_ids,
        CHANNEL_ID=int(channel_id),
        CHANNEL_LINK=channel_link,
        DATABASE_PATH=os.getenv("DATABASE_PATH", "bot.db"),
        TIMEZONE=os.getenv("TIMEZONE", "Europe/Moscow"),
    )