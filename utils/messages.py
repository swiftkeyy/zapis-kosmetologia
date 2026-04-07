from __future__ import annotations

from utils.default_data import CATEGORY_TITLES
from utils.helpers import human_date


START_TEXT = (
    "🌷 <b>Добро пожаловать!</b>\n\n"
    "Это бот для записи к <b>Шаеховой Марие</b> "
    "на косметологические услуги и массаж.\n\n"
    "Через меню ниже вы можете:\n"
    "• записаться на свободное время;\n"
    "• посмотреть свою запись;\n"
    "• открыть прайс;\n"
    "• перейти в портфолио."
)


TEXT_SETTING_TITLES = {
    "welcome_text": "Приветствие",
    "subscription_required_text": "Текст подписки",
    "subscription_failed_text": "Текст проверки подписки",
    "reminder_text": "Текст напоминания",
}


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


def format_channel_reschedule_notification(old_appointment: dict, new_appointment: dict) -> str:
    return (
        "🔁 <b>Перенос записи</b>\n\n"
        f"Клиент: <b>{new_appointment['full_name']}</b>\n"
        f"Услуга: <b>{new_appointment['service_name']}</b>\n"
        f"Было: <b>{human_date(old_appointment['work_date'])}</b> в <b>{old_appointment['time']}</b>\n"
        f"Стало: <b>{human_date(new_appointment['work_date'])}</b> в <b>{new_appointment['time']}</b>"
    )


def format_client_history_html(profile: dict, history: list[dict]) -> str:
    username = f"@{profile['username']}" if profile.get("username") else "—"
    blocked = "да" if profile.get("is_blocked") else "нет"
    note = profile.get("note") or "—"
    lines = [
        "👥 <b>Карточка клиента</b>",
        "",
        f"<b>Имя:</b> {profile['full_name']}",
        f"<b>Телефон:</b> {profile['phone']}",
        f"<b>Telegram:</b> {username}",
        f"<b>User ID:</b> <code>{profile['user_id']}</code>",
        f"<b>Стоп-лист:</b> {blocked}",
        f"<b>Заметка:</b> {note}",
        f"<b>Всего записей:</b> {profile.get('total_visits', 0)}",
        f"<b>Активных:</b> {profile.get('active_count', 0)}",
        f"<b>Отмен:</b> {profile.get('cancelled_count', 0)}",
        "",
        "<b>Последние записи:</b>",
    ]
    if not history:
        lines.append("История пуста.")
    else:
        for item in history[:10]:
            status = {
                "booked": "активна",
                "cancelled": "отменена",
            }.get(item["status"], item["status"])
            lines.append(f"• {human_date(item['work_date'])}, <b>{item['time']}</b> — {item['service_name']} ({status})")
    return "\n".join(lines)


def format_stats_html(title: str, start_day: str, end_day: str, stats: dict) -> str:
    lines = [
        f"📊 <b>{title}</b>",
        "",
        f"<b>Период:</b> {human_date(start_day)} — {human_date(end_day)}",
        f"<b>Всего записей:</b> {stats.get('total', 0)}",
        f"<b>Активных:</b> {stats.get('booked_count', 0)}",
        f"<b>Отмен:</b> {stats.get('cancelled_count', 0)}",
        f"<b>Потенциальная выручка:</b> {stats.get('booked_revenue', 0)}₽",
        f"<b>Свободных слотов на завтра:</b> {stats.get('free_tomorrow', 0)}",
        f"<b>Клиентов в стоп-листе:</b> {stats.get('blocked_clients', 0)}",
        "",
        "<b>Популярные услуги:</b>",
    ]
    popular = stats.get("popular_services") or []
    if not popular:
        lines.append("Пока недостаточно данных.")
    else:
        for item in popular:
            lines.append(f"• {item['name']} — {item['qty']} запис.")
    return "\n".join(lines)
