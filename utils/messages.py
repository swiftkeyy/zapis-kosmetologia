from __future__ import annotations

from utils.default_data import CATEGORY_TITLES
from utils.helpers import human_date


def format_appointment_html(appointment: dict) -> str:
    category_title = CATEGORY_TITLES.get(appointment["category"], appointment["category"])
    return (
        "<b>Ваша запись</b>\n\n"
        f"<b>Дата:</b> {human_date(appointment['work_date'])}\n"
        f"<b>Время:</b> {appointment['time']}\n"
        f"<b>Категория:</b> {category_title}\n"
        f"<b>Услуга:</b> {appointment['service_name']}\n"
        f"<b>Стоимость:</b> {appointment['price']}₽\n"
        f"<b>Имя:</b> {appointment['full_name']}\n"
        f"<b>Телефон:</b> {appointment['phone']}"
    )


def format_admin_appointment_notification(appointment: dict) -> str:
    category_title = CATEGORY_TITLES.get(appointment["category"], appointment["category"])
    username = f"@{appointment['username']}" if appointment.get("username") else "—"
    return (
        "📥 <b>Новая запись</b>\n\n"
        f"<b>Дата:</b> {human_date(appointment['work_date'])}\n"
        f"<b>Время:</b> {appointment['time']}\n"
        f"<b>Категория:</b> {category_title}\n"
        f"<b>Услуга:</b> {appointment['service_name']}\n"
        f"<b>Стоимость:</b> {appointment['price']}₽\n"
        f"<b>Клиент:</b> {appointment['full_name']}\n"
        f"<b>Телефон:</b> {appointment['phone']}\n"
        f"<b>Telegram:</b> {username}\n"
        f"<b>User ID:</b> <code>{appointment['user_id']}</code>"
    )


def format_channel_booking_notification(appointment: dict) -> str:
    return (
        "🗓 <b>Обновление расписания</b>\n\n"
        f"🔹 Новая запись на <b>{human_date(appointment['work_date'])}</b>\n"
        f"🕒 Время: <b>{appointment['time']}</b>\n"
        f"💼 Услуга: <b>{appointment['service_name']}</b>\n"
        f"👤 Клиент: <b>{appointment['full_name']}</b>"
    )


def format_channel_cancellation_notification(appointment: dict) -> str:
    return (
        "❌ <b>Отмена записи</b>\n\n"
        f"Дата: <b>{human_date(appointment['work_date'])}</b>\n"
        f"Время: <b>{appointment['time']}</b>\n"
        f"Услуга: <b>{appointment['service_name']}</b>\n"
        f"Клиент: <b>{appointment['full_name']}</b>"
    )
