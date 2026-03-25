from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Config:
    """Конфигурация приложения."""

    BOT_TOKEN: str
    ADMIN_IDS: list[int]
    SUBSCRIBE_CHANNEL_ID: int
    SUBSCRIBE_CHANNEL_LINK: str
    SCHEDULE_CHANNEL_ID: int
    DATABASE_PATH: str = "bot.db"
    TIMEZONE: str = "Europe/Moscow"


def _parse_admin_ids() -> list[int]:
    """Поддерживает и новый ADMIN_IDS, и старый ADMIN_ID."""

    admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
    admin_id_raw = os.getenv("ADMIN_ID", "").strip()

    if admin_ids_raw:
        values = [item.strip() for item in admin_ids_raw.split(",") if item.strip()]
    elif admin_id_raw:
        values = [admin_id_raw]
    else:
        raise ValueError("Не найден ADMIN_IDS или ADMIN_ID в .env")

    try:
        return [int(value) for value in values]
    except ValueError as exc:
        raise ValueError("ADMIN_IDS должен содержать только числовые Telegram ID") from exc


def _require_int_env(*names: str) -> int:
    """Возвращает первое найденное числовое значение из списка имён переменных."""

    for name in names:
        raw = os.getenv(name, "").strip()
        if raw:
            try:
                return int(raw)
            except ValueError as exc:
                raise ValueError(f"Переменная {name} должна быть числом, получено: {raw!r}") from exc
    joined = " или ".join(names)
    raise ValueError(f"Не найдена переменная {joined} в .env")


def _require_str_env(*names: str) -> str:
    """Возвращает первое найденное непустое строковое значение из списка имён переменных."""

    for name in names:
        raw = os.getenv(name, "").strip()
        if raw:
            return raw
    joined = " или ".join(names)
    raise ValueError(f"Не найдена переменная {joined} в .env")


def load_config() -> Config:
    """Загружает конфиг из .env.

    Поддерживаются два формата:
    1) Новый:
       ADMIN_IDS, SUBSCRIBE_CHANNEL_ID, SUBSCRIBE_CHANNEL_LINK, SCHEDULE_CHANNEL_ID
    2) Старый:
       ADMIN_ID, CHANNEL_ID, CHANNEL_LINK
    """

    bot_token = _require_str_env("BOT_TOKEN")
    admin_ids = _parse_admin_ids()
    subscribe_channel_id = _require_int_env("SUBSCRIBE_CHANNEL_ID", "CHANNEL_ID")
    subscribe_channel_link = _require_str_env("SUBSCRIBE_CHANNEL_LINK", "CHANNEL_LINK")
    schedule_channel_id = _require_int_env("SCHEDULE_CHANNEL_ID", "CHANNEL_ID")

    return Config(
        BOT_TOKEN=bot_token,
        ADMIN_IDS=admin_ids,
        SUBSCRIBE_CHANNEL_ID=subscribe_channel_id,
        SUBSCRIBE_CHANNEL_LINK=subscribe_channel_link,
        SCHEDULE_CHANNEL_ID=schedule_channel_id,
        DATABASE_PATH=os.getenv("DATABASE_PATH", "bot.db").strip() or "bot.db",
        TIMEZONE=os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow",
    )
