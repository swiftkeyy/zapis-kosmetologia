from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database.db import Database
from keyboards.callbacks import (
    AdminCb,
    AppointmentAdminCb,
    AppointmentMoveSlotCb,
    CalendarCb,
    CategoryCb,
    MenuCb,
    ServiceAdminCb,
    SlotAdminCb,
)
from keyboards.inline import (
    build_calendar_keyboard,
    get_admin_appointment_cancel_confirm_kb,
    get_admin_appointment_manage_kb,
    get_admin_appointments_kb,
    get_admin_category_kb,
    get_admin_menu_kb,
    get_admin_price_menu_kb,
    get_admin_service_card_kb,
    get_admin_services_delete_kb,
    get_admin_services_manage_kb,
    get_admin_slots_delete_kb,
    get_admin_transfer_slots_kb,
    get_back_menu_kb,
)
from services.scheduler import ReminderScheduler
from states.admin import AdminStates
from utils.default_data import CATEGORY_TITLES
from utils.helpers import human_date
from utils.messages import (
    format_channel_cancellation_notification,
    format_channel_reschedule_notification,
)


router = Router(name="admin")


def get_admin_ids(config: Config) -> list[int]:
    admin_ids = getattr(config, "ADMIN_IDS", None)
    if admin_ids:
        return list(admin_ids)
    admin_id = getattr(config, "ADMIN_ID", None)
    return [admin_id] if admin_id else []


def is_admin(user_id: int, config: Config) -> bool:
    return user_id in get_admin_ids(config)


def get_schedule_channel_id(config: Config) -> int | None:
    return getattr(config, "SCHEDULE_CHANNEL_ID", None) or getattr(config, "CHANNEL_ID", None)


def admin_enabled_dates(days: int = 90) -> set[date]:
    today = date.today()
    return {today + timedelta(days=offset) for offset in range(days + 1)}


async def open_admin_calendar(callback: CallbackQuery, scope: str, title: str) -> None:
    today = date.today()
    max_date = today + timedelta(days=90)
    enabled = admin_enabled_dates(90)
    await callback.message.edit_text(
        title,
        reply_markup=build_calendar_keyboard(
            scope=scope,
            year=today.year,
            month=today.month,
            enabled_dates=enabled,
            min_date=today,
            max_date=max_date,
        ),
    )
    await callback.answer()


async def render_service_card(message: Message | CallbackQuery, service: dict) -> None:
    text = (
        "💼 <b>Карточка услуги</b>\n\n"
        f"<b>Название:</b> {service['name']}\n"
        f"<b>Категория:</b> {service['category_title']}\n"
        f"<b>Цена:</b> {service['price']}₽\n"
        f"<b>Статус:</b> {'активна' if service['is_active'] else 'скрыта'}"
    )
    if service.get("description"):
        text += f"\n<b>Описание:</b> {service['description']}"

    reply_markup = get_admin_service_card_kb(service["id"], bool(service["is_active"]))
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=reply_markup)
        await message.answer()
    else:
        await message.answer(text, reply_markup=reply_markup)


async def render_appointments_for_date(target: CallbackQuery, db: Database, selected_date: str) -> None:
    appointments = await db.get_appointments_by_date(selected_date)
    if not appointments:
        await target.message.edit_text(
            f"На <b>{human_date(selected_date)}</b> активных записей нет.",
            reply_markup=get_admin_menu_kb(),
        )
        await target.answer()
        return

    await target.message.edit_text(
        f"📋 <b>Записи на {human_date(selected_date)}</b>\n\nВыберите запись:",
        reply_markup=get_admin_appointments_kb(appointments),
    )
    await target.answer()


async def render_appointment_card(callback: CallbackQuery, appointment: dict) -> None:
    category_title = CATEGORY_TITLES.get(appointment["category"], appointment["category"])
    username = f"@{appointment['username']}" if appointment.get("username") else "—"
    text = (
        "📌 <b>Карточка записи</b>\n\n"
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
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_appointment_manage_kb(appointment["id"]),
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.action == "admin"))
async def admin_panel(callback: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "⚙️ <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_menu_kb(),
    )
    await callback.answer()


@router.callback_query(AdminCb.filter(F.action == "prices"))
async def admin_prices_menu(callback: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "💰 <b>Управление услугами</b>\n\nВыберите действие:",
        reply_markup=get_admin_price_menu_kb(),
    )
    await callback.answer()


@router.callback_query(AdminCb.filter(F.action == "manage_services"))
async def admin_manage_services_menu(callback: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    await state.clear()
    await state.update_data(admin_action="manage_services")
    await callback.message.edit_text(
        "Выберите категорию услуг для редактирования:",
        reply_markup=get_admin_category_kb(back_action="prices"),
    )
    await callback.answer()


@router.callback_query(AdminCb.filter(F.action == "appointments_by_date"))
async def admin_appointments_by_date(callback: CallbackQuery, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    await open_admin_calendar(callback, "ap", "📋 <b>Записи по дате</b>\n\nВыберите дату:")


@router.callback_query(AdminCb.filter(F.action == "add_day"))
async def admin_add_day(callback: CallbackQuery, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    await open_admin_calendar(callback, "ad", "➕ <b>Добавить рабочий день</b>\n\nВыберите дату:")


@router.callback_query(AdminCb.filter(F.action == "add_slots"))
async def admin_add_slots(callback: CallbackQuery, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    await open_admin_calendar(callback, "as", "🕒 <b>Добавить временные слоты</b>\n\nВыберите дату:")


@router.callback_query(AdminCb.filter(F.action == "delete_slot"))
async def admin_delete_slots(callback: CallbackQuery, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    await open_admin_calendar(callback, "ds", "🗑 <b>Удалить временный слот</b>\n\nВыберите дату:")


@router.callback_query(AdminCb.filter(F.action == "schedule"))
async def admin_schedule(callback: CallbackQuery, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    await open_admin_calendar(callback, "sd", "📅 <b>Расписание на дату</b>\n\nВыберите день:")


@router.callback_query(AdminCb.filter(F.action == "close_day"))
async def admin_close_day(callback: CallbackQuery, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    await open_admin_calendar(callback, "cd", "🚫 <b>Полностью закрыть день</b>\n\nВыберите дату:")


@router.callback_query(AdminCb.filter(F.action == "cancel_client"))
async def admin_cancel_client(callback: CallbackQuery, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    await open_admin_calendar(callback, "ap", "📋 <b>Выберите дату записи клиента</b>\n\nДалее можно отменить или перенести запись.")


@router.callback_query(AdminCb.filter(F.action == "add_service"))
async def admin_add_service(callback: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    await state.clear()
    await state.update_data(admin_action="add_service")
    await callback.message.edit_text(
        "Выберите категорию для новой услуги:",
        reply_markup=get_admin_category_kb(back_action="prices"),
    )
    await callback.answer()


@router.callback_query(AdminCb.filter(F.action == "delete_service"))
async def admin_delete_service_menu(callback: CallbackQuery, config: Config, db: Database) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    services = await db.get_services(only_active=False)
    if not services:
        await callback.message.edit_text(
            "Услуг пока нет.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выберите услугу для удаления из базы:",
        reply_markup=get_admin_services_delete_kb(services),
    )
    await callback.answer()


@router.callback_query(CalendarCb.filter(F.day == 0))
async def admin_calendar_nav(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
) -> None:
    if callback_data.scope not in {"ad", "as", "ds", "sd", "cd", "cc", "ap", "mv"}:
        return

    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    today = date.today()
    max_date = today + timedelta(days=90)
    titles = {
        "ad": "➕ <b>Добавить рабочий день</b>\n\nВыберите дату:",
        "as": "🕒 <b>Добавить временные слоты</b>\n\nВыберите дату:",
        "ds": "🗑 <b>Удалить временный слот</b>\n\nВыберите дату:",
        "sd": "📅 <b>Расписание на дату</b>\n\nВыберите день:",
        "cd": "🚫 <b>Полностью закрыть день</b>\n\nВыберите дату:",
        "cc": "❌ <b>Отмена записи клиента</b>\n\nВыберите дату:",
        "ap": "📋 <b>Записи по дате</b>\n\nВыберите дату:",
        "mv": "🔁 <b>Перенос записи</b>\n\nВыберите новую дату:",
    }

    await callback.message.edit_text(
        titles[callback_data.scope],
        reply_markup=build_calendar_keyboard(
            scope=callback_data.scope,
            year=callback_data.year,
            month=callback_data.month,
            enabled_dates=admin_enabled_dates(90),
            min_date=today,
            max_date=max_date,
        ),
    )
    await callback.answer()


@router.callback_query(CalendarCb.filter((F.scope == "ad") & (F.day > 0)))
async def admin_pick_add_day(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    selected = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
    await db.add_work_day(selected)
    await callback.message.edit_text(
        f"✅ Рабочий день <b>{human_date(selected)}</b> добавлен.",
        reply_markup=get_admin_menu_kb(),
    )
    await callback.answer()


@router.callback_query(CalendarCb.filter((F.scope == "as") & (F.day > 0)))
async def admin_pick_add_slots_date(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
    db: Database,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    selected = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
    await db.add_work_day(selected)
    await state.set_state(AdminStates.add_slots_time)
    await state.update_data(admin_action="add_slots", selected_date=selected)

    await callback.message.edit_text(
        f"Введите время для <b>{human_date(selected)}</b> через запятую.\n\n"
        f"Пример: <code>10:00, 11:30, 14:00</code>",
        reply_markup=get_back_menu_kb(),
    )
    await callback.answer()


@router.callback_query(CalendarCb.filter((F.scope == "ds") & (F.day > 0)))
async def admin_pick_delete_slots_date(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    selected = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
    slots = await db.get_all_slots_for_admin(selected)
    if not slots:
        await callback.message.edit_text(
            f"На дату <b>{human_date(selected)}</b> слотов нет.",
            reply_markup=get_admin_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Слоты на <b>{human_date(selected)}</b>:",
        reply_markup=get_admin_slots_delete_kb(slots),
    )
    await callback.answer()


@router.callback_query(CalendarCb.filter((F.scope == "sd") & (F.day > 0)))
async def admin_pick_schedule_date(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    selected = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
    summary = await db.get_day_summary(selected)

    lines = [f"📅 <b>Расписание на {human_date(selected)}</b>\n"]

    work_day = summary["work_day"]
    if not work_day:
        lines.append("Рабочий день не создан.")
    else:
        lines.append(f"Статус дня: {'закрыт' if work_day['is_closed'] else 'открыт'}")

    if summary["appointments"]:
        lines.append("\n<b>Записи клиентов:</b>")
        for item in summary["appointments"]:
            category = CATEGORY_TITLES.get(item["category"], item["category"])
            lines.append(
                f"• <b>{item['time']}</b> — {item['full_name']} | {item['phone']} | {category}: {item['service_name']}"
            )
    else:
        lines.append("\n<b>Записей нет.</b>")

    free_slots = [slot["time"] for slot in summary["slots"] if slot["is_active"] and not slot["is_booked"]]
    if free_slots:
        lines.append("\n<b>Свободные слоты:</b>")
        lines.append(", ".join(free_slots))
    else:
        lines.append("\nСвободных слотов нет.")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=get_admin_menu_kb(),
    )
    await callback.answer()


@router.callback_query(CalendarCb.filter((F.scope == "ap") & (F.day > 0)))
async def admin_pick_appointments_date(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    selected = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
    await render_appointments_for_date(callback, db, selected)


@router.callback_query(CalendarCb.filter((F.scope == "mv") & (F.day > 0)))
async def admin_pick_move_date(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
    db: Database,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    data = await state.get_data()
    appointment_id = data.get("transfer_appointment_id")
    if not appointment_id:
        await state.clear()
        await callback.message.edit_text("Не найдена запись для переноса.", reply_markup=get_admin_menu_kb())
        await callback.answer()
        return

    selected = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
    slots = await db.get_available_slots(selected)
    if not slots:
        await callback.message.edit_text(
            f"На <b>{human_date(selected)}</b> нет свободных слотов. Выберите другую дату.",
            reply_markup=get_admin_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(AdminStates.transfer_choose_slot)
    await state.update_data(transfer_date=selected)
    await callback.message.edit_text(
        f"🔁 <b>Перенос записи</b>\n\nВыберите новое время на <b>{human_date(selected)}</b>:",
        reply_markup=get_admin_transfer_slots_kb(appointment_id, slots),
    )
    await callback.answer()


@router.callback_query(CalendarCb.filter((F.scope == "cd") & (F.day > 0)))
async def admin_pick_close_day(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
    db: Database,
    scheduler: ReminderScheduler,
    bot: Bot,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    selected = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
    cancelled = await db.close_day_and_cancel_appointments(selected)
    schedule_channel_id = get_schedule_channel_id(config)

    for appointment in cancelled:
        scheduler.remove_job(appointment.get("reminder_job_id"))
        await db.update_appointment_reminder_job(appointment["id"], None)
        try:
            await bot.send_message(
                appointment["user_id"],
                "❌ <b>Ваша запись была отменена администратором.</b>\n\n"
                f"Дата: {human_date(selected)}\n"
                f"Время: {appointment['time']}\n"
                "При необходимости вы можете выбрать другую дату.",
                parse_mode="HTML",
            )
        except Exception:
            pass

        if schedule_channel_id:
            try:
                await bot.send_message(
                    schedule_channel_id,
                    format_channel_cancellation_notification(appointment),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    text = (
        f"🚫 День <b>{human_date(selected)}</b> закрыт полностью.\n"
        f"Отменено записей: <b>{len(cancelled)}</b>."
    )
    await callback.message.edit_text(text, reply_markup=get_admin_menu_kb())
    await callback.answer()


@router.callback_query(CategoryCb.filter())
async def admin_pick_service_category(
    callback: CallbackQuery,
    callback_data: CategoryCb,
    config: Config,
    state: FSMContext,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        return

    data = await state.get_data()
    action = data.get("admin_action")
    if action == "add_service":
        await state.update_data(category=callback_data.category)
        await state.set_state(AdminStates.add_service_name)
        category_title = CATEGORY_TITLES.get(callback_data.category, callback_data.category)
        await callback.message.edit_text(
            f"Категория выбрана: <b>{category_title}</b>\n\nВведите название новой услуги:",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    if action == "manage_services":
        services = await db.get_services_for_admin(callback_data.category)
        category_title = CATEGORY_TITLES.get(callback_data.category, callback_data.category)
        if not services:
            await callback.message.edit_text(
                f"В категории <b>{category_title}</b> услуг пока нет.",
                reply_markup=get_admin_price_menu_kb(),
            )
            await callback.answer()
            return
        await state.update_data(selected_service_category=callback_data.category)
        await callback.message.edit_text(
            f"✏️ <b>{category_title}</b>\n\nВыберите услугу:",
            reply_markup=get_admin_services_manage_kb(services),
        )
        await callback.answer()


@router.callback_query(ServiceAdminCb.filter(F.action == "view"))
async def admin_view_service(callback: CallbackQuery, callback_data: ServiceAdminCb, config: Config, db: Database) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    service = await db.get_service(callback_data.service_id)
    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return
    await render_service_card(callback, service)


@router.callback_query(ServiceAdminCb.filter(F.action == "back"))
async def admin_back_to_services(callback: CallbackQuery, callback_data: ServiceAdminCb, config: Config, db: Database) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    service = await db.get_service(callback_data.service_id)
    if not service:
        await callback.message.edit_text("Услуга не найдена.", reply_markup=get_admin_price_menu_kb())
        await callback.answer()
        return
    services = await db.get_services_for_admin(service["category"])
    await callback.message.edit_text(
        f"✏️ <b>{service['category_title']}</b>\n\nВыберите услугу:",
        reply_markup=get_admin_services_manage_kb(services),
    )
    await callback.answer()


@router.callback_query(ServiceAdminCb.filter(F.action == "edit_name"))
async def admin_edit_service_name_start(
    callback: CallbackQuery,
    callback_data: ServiceAdminCb,
    config: Config,
    db: Database,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    service = await db.get_service(callback_data.service_id)
    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return
    await state.set_state(AdminStates.edit_service_name)
    await state.update_data(edit_service_id=service["id"])
    await callback.message.edit_text(
        f"Текущее название: <b>{service['name']}</b>\n\nВведите новое название услуги:",
        reply_markup=get_back_menu_kb(),
    )
    await callback.answer()


@router.callback_query(ServiceAdminCb.filter(F.action == "edit_price"))
async def admin_edit_service_price_start(
    callback: CallbackQuery,
    callback_data: ServiceAdminCb,
    config: Config,
    db: Database,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    service = await db.get_service(callback_data.service_id)
    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return
    await state.set_state(AdminStates.edit_service_price)
    await state.update_data(edit_service_id=service["id"])
    await callback.message.edit_text(
        f"Текущая цена: <b>{service['price']}₽</b>\n\nВведите новую цену:",
        reply_markup=get_back_menu_kb(),
    )
    await callback.answer()


@router.callback_query(ServiceAdminCb.filter(F.action == "toggle"))
async def admin_toggle_service(
    callback: CallbackQuery,
    callback_data: ServiceAdminCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    service = await db.get_service(callback_data.service_id)
    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return
    await db.set_service_active(service["id"], not bool(service["is_active"]))
    updated = await db.get_service(service["id"])
    await render_service_card(callback, updated)


@router.callback_query(ServiceAdminCb.filter(F.action == "delete"))
async def admin_delete_service(
    callback: CallbackQuery,
    callback_data: ServiceAdminCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    service = await db.get_service(callback_data.service_id)
    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return

    await db.disable_service(service["id"])
    await callback.message.edit_text(
        f"🗑 Услуга <b>{service['name']}</b> скрыта и убрана из записи.",
        reply_markup=get_admin_price_menu_kb(),
    )
    await callback.answer("Услуга скрыта")


@router.message(AdminStates.add_service_name)
async def admin_get_service_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("Название слишком короткое. Повторите ввод.")
        return

    await state.update_data(service_name=name)
    await state.set_state(AdminStates.add_service_price)
    await message.answer("Введите цену в рублях, например: <code>2500</code>")


@router.message(AdminStates.add_service_price)
async def admin_get_service_price(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace("₽", "").replace(" ", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("Введите корректную цену числом.")
        return

    await state.update_data(service_price=int(raw))
    await state.set_state(AdminStates.add_service_description)
    await message.answer("Введите описание услуги или отправьте <code>-</code>.")


@router.message(AdminStates.add_service_description)
async def admin_get_service_description(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    data = await state.get_data()
    description = "" if message.text.strip() == "-" else message.text.strip()

    await db.add_service(
        name=data["service_name"],
        category=data["category"],
        price=int(data["service_price"]),
        description=description,
    )
    await state.clear()

    await message.answer(
        "✅ Услуга добавлена в прайс.",
        reply_markup=get_admin_menu_kb(),
    )


@router.message(AdminStates.edit_service_name)
async def admin_save_service_name(message: Message, state: FSMContext, db: Database) -> None:
    new_name = message.text.strip()
    if len(new_name) < 3:
        await message.answer("Название слишком короткое. Повторите ввод.")
        return

    data = await state.get_data()
    service_id = data.get("edit_service_id")
    if not service_id:
        await state.clear()
        await message.answer("Услуга не найдена.", reply_markup=get_admin_menu_kb())
        return

    await db.update_service_name(int(service_id), new_name)
    await state.clear()
    service = await db.get_service(int(service_id))
    await render_service_card(message, service)


@router.message(AdminStates.edit_service_price)
async def admin_save_service_price(message: Message, state: FSMContext, db: Database) -> None:
    raw = message.text.strip().replace("₽", "").replace(" ", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("Введите корректную цену числом.")
        return

    data = await state.get_data()
    service_id = data.get("edit_service_id")
    if not service_id:
        await state.clear()
        await message.answer("Услуга не найдена.", reply_markup=get_admin_menu_kb())
        return

    await db.update_service_price(int(service_id), int(raw))
    await state.clear()
    service = await db.get_service(int(service_id))
    await render_service_card(message, service)


@router.message(AdminStates.add_slots_time)
async def admin_add_slots_time(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    data = await state.get_data()
    selected_date = data.get("selected_date")
    if not selected_date:
        await state.clear()
        await message.answer("Дата не найдена.", reply_markup=get_admin_menu_kb())
        return

    raw_items = [item.strip() for item in message.text.split(",") if item.strip()]
    if not raw_items:
        await message.answer("Укажите хотя бы одно время.")
        return

    valid_times: list[str] = []
    for item in raw_items:
        try:
            datetime.strptime(item, "%H:%M")
            valid_times.append(item)
        except ValueError:
            await message.answer(f"Некорректный формат времени: <code>{item}</code>")
            return

    for time_value in valid_times:
        await db.add_time_slot(selected_date, time_value)

    await state.clear()
    await message.answer(
        f"✅ Добавлены слоты на <b>{human_date(selected_date)}</b>:\n" + ", ".join(valid_times),
        reply_markup=get_admin_menu_kb(),
    )


@router.callback_query(SlotAdminCb.filter(F.action == "delete"))
async def admin_delete_slot_action(
    callback: CallbackQuery,
    callback_data: SlotAdminCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    slot = await db.get_slot(callback_data.slot_id)
    if not slot:
        await callback.answer("Слот не найден.", show_alert=True)
        return

    success = await db.disable_time_slot(slot["id"])
    if not success:
        await callback.answer("Нельзя скрыть слот: на него уже есть запись.", show_alert=True)
        return

    slots = await db.get_all_slots_for_admin(slot["work_date"])
    await callback.message.edit_text(
        f"Слоты на <b>{human_date(slot['work_date'])}</b>:",
        reply_markup=get_admin_slots_delete_kb(slots),
    )
    await callback.answer("Слот скрыт")


@router.callback_query(AppointmentAdminCb.filter(F.action == "view"))
async def admin_view_appointment(
    callback: CallbackQuery,
    callback_data: AppointmentAdminCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    appointment = await db.get_appointment(callback_data.appointment_id)
    if not appointment or appointment["status"] != "booked":
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await render_appointment_card(callback, appointment)


@router.callback_query(AppointmentAdminCb.filter(F.action == "date_list"))
async def admin_back_to_date_list(
    callback: CallbackQuery,
    callback_data: AppointmentAdminCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    appointment = await db.get_appointment(callback_data.appointment_id)
    if not appointment:
        await callback.message.edit_text("Запись не найдена.", reply_markup=get_admin_menu_kb())
        await callback.answer()
        return
    await render_appointments_for_date(callback, db, appointment["work_date"])


@router.callback_query(AppointmentAdminCb.filter(F.action == "cancel_confirm"))
async def admin_cancel_confirm(
    callback: CallbackQuery,
    callback_data: AppointmentAdminCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    appointment = await db.get_appointment(callback_data.appointment_id)
    if not appointment or appointment["status"] != "booked":
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Отменить запись клиента <b>{appointment['full_name']}</b> на <b>{human_date(appointment['work_date'])}</b> в <b>{appointment['time']}</b>?",
        reply_markup=get_admin_appointment_cancel_confirm_kb(appointment["id"]),
    )
    await callback.answer()


@router.callback_query(AppointmentAdminCb.filter(F.action == "cancel"))
async def admin_cancel_appointment(
    callback: CallbackQuery,
    callback_data: AppointmentAdminCb,
    config: Config,
    db: Database,
    scheduler: ReminderScheduler,
    bot: Bot,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    appointment = await db.get_appointment(callback_data.appointment_id)
    if not appointment or appointment["status"] != "booked":
        await callback.answer("Активная запись не найдена.", show_alert=True)
        return

    scheduler.remove_job(appointment.get("reminder_job_id"))
    await db.cancel_appointment(appointment["id"], cancelled_by="admin")
    await db.update_appointment_reminder_job(appointment["id"], None)

    try:
        await bot.send_message(
            appointment["user_id"],
            "❌ <b>Ваша запись отменена администратором.</b>\n\n"
            f"Дата: {human_date(appointment['work_date'])}\n"
            f"Время: {appointment['time']}\n"
            "Вы можете выбрать другое свободное время в боте.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    schedule_channel_id = get_schedule_channel_id(config)
    if schedule_channel_id:
        try:
            await bot.send_message(
                schedule_channel_id,
                format_channel_cancellation_notification(appointment),
                parse_mode="HTML",
            )
        except Exception:
            pass

    await callback.message.edit_text(
        "✅ Запись отменена. Слот снова доступен для записи.",
        reply_markup=get_admin_menu_kb(),
    )
    await callback.answer("Запись отменена")


@router.callback_query(AppointmentAdminCb.filter(F.action == "move"))
async def admin_start_move_appointment(
    callback: CallbackQuery,
    callback_data: AppointmentAdminCb,
    config: Config,
    db: Database,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    appointment = await db.get_appointment(callback_data.appointment_id)
    if not appointment or appointment["status"] != "booked":
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    await state.set_state(AdminStates.transfer_choose_date)
    await state.update_data(transfer_appointment_id=appointment["id"])
    await open_admin_calendar(callback, "mv", "🔁 <b>Перенос записи</b>\n\nВыберите новую дату:")


@router.callback_query(AppointmentMoveSlotCb.filter())
async def admin_finish_move_appointment(
    callback: CallbackQuery,
    callback_data: AppointmentMoveSlotCb,
    config: Config,
    db: Database,
    scheduler: ReminderScheduler,
    bot: Bot,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    appointment = await db.get_appointment(callback_data.appointment_id)
    new_slot = await db.get_slot(callback_data.slot_id)
    if not appointment or appointment["status"] != "booked" or not new_slot:
        await callback.answer("Не удалось перенести запись.", show_alert=True)
        return

    available_slots = await db.get_available_slots(new_slot["work_date"])
    if not any(item["id"] == new_slot["id"] for item in available_slots):
        await callback.answer("Этот слот уже занят.", show_alert=True)
        return

    old_appointment = dict(appointment)
    scheduler.remove_job(appointment.get("reminder_job_id"))
    try:
        await db.reschedule_appointment(appointment["id"], new_slot["id"])
    except sqlite3.IntegrityError:
        await callback.answer("Этот слот уже занят.", show_alert=True)
        return

    await scheduler.schedule_appointment_reminder(appointment["id"])
    updated_appointment = await db.get_appointment(appointment["id"])
    await state.clear()

    try:
        await bot.send_message(
            updated_appointment["user_id"],
            "🔁 <b>Ваша запись была перенесена администратором.</b>\n\n"
            f"Новая дата: <b>{human_date(updated_appointment['work_date'])}</b>\n"
            f"Новое время: <b>{updated_appointment['time']}</b>\n"
            f"Услуга: <b>{updated_appointment['service_name']}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    schedule_channel_id = get_schedule_channel_id(config)
    if schedule_channel_id:
        try:
            await bot.send_message(
                schedule_channel_id,
                format_channel_reschedule_notification(old_appointment, updated_appointment),
                parse_mode="HTML",
            )
        except Exception:
            pass

    await callback.message.edit_text(
        "✅ Запись перенесена.\n\n"
        f"Новая дата: <b>{human_date(updated_appointment['work_date'])}</b>\n"
        f"Новое время: <b>{updated_appointment['time']}</b>",
        reply_markup=get_admin_appointment_manage_kb(updated_appointment["id"]),
    )
    await callback.answer("Запись перенесена")
