from __future__ import annotations

import calendar
import re
from datetime import date, datetime


def format_rubles(value: int) -> str:
    return f"{value}₽"


def human_date(iso_date: str) -> str:
    dt = datetime.strptime(iso_date, "%Y-%m-%d").date()
    months = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }
    weekdays = {
        0: "понедельник",
        1: "вторник",
        2: "среда",
        3: "четверг",
        4: "пятница",
        5: "суббота",
        6: "воскресенье",
    }
    return f"{dt.day} {months[dt.month]} {dt.year} ({weekdays[dt.weekday()]})"


def month_title(year: int, month: int) -> str:
    months = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь",
    }
    return f"{months[month]} {year}"


def get_month_matrix(year: int, month: int) -> list[list[int]]:
    cal = calendar.Calendar(firstweekday=0)
    return cal.monthdayscalendar(year, month)


def validate_phone(phone: str) -> bool:
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    return bool(re.fullmatch(r"(\+7|8)\d{10}", cleaned))


def normalize_phone(phone: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if cleaned.startswith("8") and len(cleaned) == 11:
        cleaned = "+7" + cleaned[1:]
    return cleaned


def within_booking_window(target_date: date, days_ahead: int = 31) -> bool:
    today = date.today()
    return today <= target_date <= today.fromordinal(today.toordinal() + days_ahead)
