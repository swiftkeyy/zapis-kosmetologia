from __future__ import annotations

from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.callbacks import (
    AdminCb,
    AppointmentAdminCb,
    AppointmentMoveSlotCb,
    CalendarCb,
    CategoryCb,
    ConfirmCb,
    MenuCb,
    ServiceAdminCb,
    ServiceCb,
    SlotAdminCb,
    SlotCb,
    SubscriptionCb,
)
from utils.default_data import CATEGORY_TITLES
from utils.helpers import get_month_matrix, month_title


def get_main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗓 Записаться", callback_data=MenuCb(action="book"))
    kb.button(text="📌 Моя запись", callback_data=MenuCb(action="my"))
    kb.button(text="💰 Прайсы", callback_data=MenuCb(action="prices"))
    kb.button(text="🖼 Портфолио", callback_data=MenuCb(action="portfolio"))
    if is_admin:
        kb.button(text="⚙️ Админ-панель", callback_data=MenuCb(action="admin"))
    kb.adjust(1)
    return kb.as_markup()


def get_back_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data=MenuCb(action="main"))
    return kb.as_markup()


def get_subscription_kb(channel_link: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📢 Подписаться", url=channel_link))
    kb.row(
        InlineKeyboardButton(
            text="✅ Проверить подписку",
            callback_data=SubscriptionCb(action="check").pack(),
        )
    )
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuCb(action="main").pack()))
    return kb.as_markup()


def build_calendar_keyboard(
    *,
    scope: str,
    year: int,
    month: int,
    enabled_dates: set[date],
    min_date: date,
    max_date: date,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    if month == 1:
        prev_candidate = date(year - 1, 12, 1)
    else:
        prev_candidate = date(year, month - 1, 1)

    if month == 12:
        next_candidate = date(year + 1, 1, 1)
    else:
        next_candidate = date(year, month + 1, 1)

    prev_allowed = prev_candidate >= date(min_date.year, min_date.month, 1)
    next_allowed = next_candidate <= date(max_date.year, max_date.month, 1)

    kb.row(
        InlineKeyboardButton(
            text="◀️",
            callback_data=CalendarCb(
                scope=scope,
                year=prev_candidate.year if prev_allowed else year,
                month=prev_candidate.month if prev_allowed else month,
                day=0,
            ).pack()
            if prev_allowed
            else "ignore",
        ),
        InlineKeyboardButton(text=month_title(year, month), callback_data="ignore"),
        InlineKeyboardButton(
            text="▶️",
            callback_data=CalendarCb(
                scope=scope,
                year=next_candidate.year if next_allowed else year,
                month=next_candidate.month if next_allowed else month,
                day=0,
            ).pack()
            if next_allowed
            else "ignore",
        ),
    )

    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    kb.row(*(InlineKeyboardButton(text=day_name, callback_data="ignore") for day_name in weekdays))

    for week in get_month_matrix(year, month):
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                continue

            current_date = date(year, month, day_num)
            selectable = current_date in enabled_dates and min_date <= current_date <= max_date
            row.append(
                InlineKeyboardButton(
                    text=f"{day_num}" if selectable else f"·{day_num}",
                    callback_data=CalendarCb(scope=scope, year=year, month=month, day=day_num).pack()
                    if selectable
                    else "ignore",
                )
            )
        kb.row(*row)

    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuCb(action="main").pack()))
    return kb.as_markup()


def get_categories_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💆 Массаж", callback_data=CategoryCb(category="massage"))
    kb.button(text="✨ Косметология", callback_data=CategoryCb(category="cosmetology"))
    kb.button(text="⬅️ В меню", callback_data=MenuCb(action="main"))
    kb.adjust(1)
    return kb.as_markup()


def get_services_kb(services: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for service in services:
        kb.button(
            text=f"{service['name']} — {service['price']}₽",
            callback_data=ServiceCb(service_id=service["id"]),
        )
    kb.button(text="⬅️ В меню", callback_data=MenuCb(action="main"))
    kb.adjust(1)
    return kb.as_markup()


def get_slots_kb(slots: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for slot in slots:
        kb.button(text=slot["time"], callback_data=SlotCb(slot_id=slot["id"]))
    kb.button(text="⬅️ В меню", callback_data=MenuCb(action="main"))
    kb.adjust(3, repeat=True)
    return kb.as_markup()


def get_booking_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=MenuCb(action="confirm_booking"))
    kb.button(text="❌ Отменить", callback_data=MenuCb(action="main"))
    kb.adjust(1)
    return kb.as_markup()


def get_my_appointment_kb(appointment_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отменить запись", callback_data=ConfirmCb(action="cancel_my", entity_id=appointment_id))
    kb.button(text="⬅️ В меню", callback_data=MenuCb(action="main"))
    kb.adjust(1)
    return kb.as_markup()


def get_confirm_cancel_kb(appointment_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, отменить", callback_data=ConfirmCb(action="cancel_yes", entity_id=appointment_id))
    kb.button(text="Нет", callback_data=MenuCb(action="my"))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить рабочий день", callback_data=AdminCb(action="add_day"))
    kb.button(text="🕒 Добавить слоты", callback_data=AdminCb(action="add_slots"))
    kb.button(text="🕘 Массово добавить слоты", callback_data=AdminCb(action="bulk_add_slots"))
    kb.button(text="🗑 Удалить слот", callback_data=AdminCb(action="delete_slot"))
    kb.button(text="💰 Управление услугами", callback_data=AdminCb(action="prices"))
    kb.button(text="👥 Клиенты", callback_data=AdminCb(action="clients"))
    kb.button(text="📋 Записи по дате", callback_data=AdminCb(action="appointments_by_date"))
    kb.button(text="📅 Расписание на дату", callback_data=AdminCb(action="schedule"))
    kb.button(text="📎 Копировать расписание", callback_data=AdminCb(action="copy_schedule"))
    kb.button(text="🚫 Закрыть день", callback_data=AdminCb(action="close_day"))
    kb.button(text="❌ Отменить запись клиента", callback_data=AdminCb(action="cancel_client"))
    kb.button(text="⬅️ В меню", callback_data=MenuCb(action="main"))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_price_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить услугу", callback_data=AdminCb(action="add_service"))
    kb.button(text="✏️ Редактировать услуги", callback_data=AdminCb(action="manage_services"))
    kb.button(text="🗑 Удалить услугу", callback_data=AdminCb(action="delete_service"))
    kb.button(text="⬅️ В админ-панель", callback_data=MenuCb(action="admin"))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_category_kb(back_action: str = "prices") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💆 Массаж", callback_data=CategoryCb(category="massage"))
    kb.button(text="✨ Косметология", callback_data=CategoryCb(category="cosmetology"))
    kb.button(text="⬅️ Назад", callback_data=AdminCb(action=back_action))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_services_delete_kb(services: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for service in services:
        title = CATEGORY_TITLES.get(service["category"], service["category"])
        kb.button(
            text=f"{title}: {service['name']} — {service['price']}₽",
            callback_data=ServiceAdminCb(action="delete", service_id=service["id"]),
        )
    kb.button(text="⬅️ Назад", callback_data=AdminCb(action="prices"))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_services_manage_kb(services: list[dict], back_action: str = "prices") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for service in services:
        status_icon = "🟢" if service.get("is_active") else "⚪️"
        kb.button(
            text=f"{status_icon} {service['name']} — {service['price']}₽",
            callback_data=ServiceAdminCb(action="view", service_id=service["id"]),
        )
    kb.button(text="⬅️ Назад", callback_data=AdminCb(action=back_action))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_service_card_kb(service_id: int, is_active: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить название", callback_data=ServiceAdminCb(action="edit_name", service_id=service_id))
    kb.button(text="💸 Изменить цену", callback_data=ServiceAdminCb(action="edit_price", service_id=service_id))
    kb.button(
        text="🙈 Скрыть" if is_active else "👁 Показать",
        callback_data=ServiceAdminCb(action="toggle", service_id=service_id),
    )
    kb.button(text="🗑 Удалить", callback_data=ServiceAdminCb(action="delete", service_id=service_id))
    kb.button(text="⬅️ К списку услуг", callback_data=ServiceAdminCb(action="back", service_id=service_id))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_slots_delete_kb(slots: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for slot in slots:
        status = "⛔ занято" if slot["is_booked"] else "🆓"
        active = "" if slot["is_active"] else " (скрыт)"
        kb.button(
            text=f"{slot['time']} {status}{active}",
            callback_data=SlotAdminCb(action="delete", slot_id=slot["id"]),
        )
    kb.button(text="⬅️ В админ-панель", callback_data=MenuCb(action="admin"))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_appointments_kb(appointments: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in appointments:
        kb.button(
            text=f"{item['time']} — {item['full_name']}",
            callback_data=AppointmentAdminCb(action="view", appointment_id=item["id"]),
        )
    kb.button(text="⬅️ В админ-панель", callback_data=MenuCb(action="admin"))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_appointment_manage_kb(appointment_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Перенести запись", callback_data=AppointmentAdminCb(action="move", appointment_id=appointment_id))
    kb.button(text="❌ Отменить запись", callback_data=AppointmentAdminCb(action="cancel_confirm", appointment_id=appointment_id))
    kb.button(text="⬅️ К списку даты", callback_data=AppointmentAdminCb(action="date_list", appointment_id=appointment_id))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_appointment_cancel_confirm_kb(appointment_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, отменить", callback_data=AppointmentAdminCb(action="cancel", appointment_id=appointment_id))
    kb.button(text="Нет", callback_data=AppointmentAdminCb(action="view", appointment_id=appointment_id))
    kb.adjust(1)
    return kb.as_markup()


def get_admin_transfer_slots_kb(appointment_id: int, slots: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for slot in slots:
        kb.button(
            text=slot["time"],
            callback_data=AppointmentMoveSlotCb(appointment_id=appointment_id, slot_id=slot["id"]),
        )
    kb.button(text="⬅️ В админ-панель", callback_data=MenuCb(action="admin"))
    kb.adjust(3, repeat=True)
    return kb.as_markup()
