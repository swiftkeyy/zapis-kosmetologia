from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Config:
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = field(default_factory=list)
    ADMIN_ID: int = 0

    SUBSCRIBE_CHANNEL_ID: int = 0
    SUBSCRIBE_CHANNEL_LINK: str = ""
    SCHEDULE_CHANNEL_ID: int = 0

    # совместимость со старым кодом
    CHANNEL_ID: int = 0
    CHANNEL_LINK: str = ""

    DATABASE_PATH: str = "bot.db"
    TIMEZONE: str = "Europe/Moscow"


def _parse_admin_ids() -> tuple[list[int], int]:
    admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
    admin_id_raw = os.getenv("ADMIN_ID", "").strip()

    admin_ids: list[int] = []

    if admin_ids_raw:
        admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()]
    elif admin_id_raw:
        admin_ids = [int(admin_id_raw)]

    if not admin_ids:
        raise ValueError("Не найден ADMIN_ID или ADMIN_IDS в переменных окружения")

    return admin_ids, admin_ids[0]


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("Не найден BOT_TOKEN в переменных окружения")

    admin_ids, first_admin_id = _parse_admin_ids()

    subscribe_channel_id = os.getenv("SUBSCRIBE_CHANNEL_ID", "").strip()
    subscribe_channel_link = os.getenv("SUBSCRIBE_CHANNEL_LINK", "").strip()
    schedule_channel_id = os.getenv("SCHEDULE_CHANNEL_ID", "").strip()

    channel_id = os.getenv("CHANNEL_ID", "").strip()
    channel_link = os.getenv("CHANNEL_LINK", "").strip()

    final_subscribe_channel_id = subscribe_channel_id or channel_id
    final_subscribe_channel_link = subscribe_channel_link or channel_link
    final_schedule_channel_id = schedule_channel_id or channel_id

    if not final_subscribe_channel_id:
        raise ValueError("Не найден SUBSCRIBE_CHANNEL_ID или CHANNEL_ID")
    if not final_subscribe_channel_link:
        raise ValueError("Не найден SUBSCRIBE_CHANNEL_LINK или CHANNEL_LINK")
    if not final_schedule_channel_id:
        raise ValueError("Не найден SCHEDULE_CHANNEL_ID или CHANNEL_ID")

    return Config(
        BOT_TOKEN=bot_token,
        ADMIN_IDS=admin_ids,
        ADMIN_ID=first_admin_id,
        SUBSCRIBE_CHANNEL_ID=int(final_subscribe_channel_id),
        SUBSCRIBE_CHANNEL_LINK=final_subscribe_channel_link,
        SCHEDULE_CHANNEL_ID=int(final_schedule_channel_id),
        CHANNEL_ID=int(final_subscribe_channel_id),
        CHANNEL_LINK=final_subscribe_channel_link,
        DATABASE_PATH=os.getenv("DATABASE_PATH", "bot.db"),
        TIMEZONE=os.getenv("TIMEZONE", "Europe/Samara"),
    )
