from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Config:
    """Конфигурация приложения."""

    BOT_TOKEN: str
<<<<<<< HEAD

    ADMIN_IDS: list[int] = field(default_factory=list)
    ADMIN_ID: int = 0

    SUBSCRIBE_CHANNEL_ID: int = 0
    SUBSCRIBE_CHANNEL_LINK: str = ""
    SCHEDULE_CHANNEL_ID: int = 0

    # совместимость со старым кодом
    CHANNEL_ID: int = 0
    CHANNEL_LINK: str = ""

=======
    ADMIN_IDS: list[int]
    SUBSCRIBE_CHANNEL_ID: int
    SUBSCRIBE_CHANNEL_LINK: str
    SCHEDULE_CHANNEL_ID: int
>>>>>>> a551ec1 (fix indentation in booking)
    DATABASE_PATH: str = "bot.db"
    TIMEZONE: str = "Europe/Samara"


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


<<<<<<< HEAD
def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("Не найден BOT_TOKEN в переменных окружения")

    admin_ids, first_admin_id = _parse_admin_ids()

    subscribe_channel_id = os.getenv("SUBSCRIBE_CHANNEL_ID", "").strip()
    subscribe_channel_link = os.getenv("SUBSCRIBE_CHANNEL_LINK", "").strip()
    schedule_channel_id = os.getenv("SCHEDULE_CHANNEL_ID", "").strip()

    # старые переменные для совместимости
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
=======
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
>>>>>>> a551ec1 (fix indentation in booking)

    return Config(
        BOT_TOKEN=bot_token,
        ADMIN_IDS=admin_ids,
<<<<<<< HEAD
        ADMIN_ID=first_admin_id,
        SUBSCRIBE_CHANNEL_ID=int(final_subscribe_channel_id),
        SUBSCRIBE_CHANNEL_LINK=final_subscribe_channel_link,
        SCHEDULE_CHANNEL_ID=int(final_schedule_channel_id),
        CHANNEL_ID=int(final_subscribe_channel_id),
        CHANNEL_LINK=final_subscribe_channel_link,
        DATABASE_PATH=os.getenv("DATABASE_PATH", "bot.db"),
        TIMEZONE=os.getenv("TIMEZONE", "Europe/Samara"),
=======
        SUBSCRIBE_CHANNEL_ID=subscribe_channel_id,
        SUBSCRIBE_CHANNEL_LINK=subscribe_channel_link,
        SCHEDULE_CHANNEL_ID=schedule_channel_id,
        DATABASE_PATH=os.getenv("DATABASE_PATH", "bot.db").strip() or "bot.db",
        TIMEZONE=os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow",
>>>>>>> a551ec1 (fix indentation in booking)
    )
