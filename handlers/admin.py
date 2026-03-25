from __future__ import annotations

from datetime import date, datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database.db import Database
from keyboards.callbacks import (
    AdminCb,
    AppointmentAdminCb,
    CalendarCb,
    CategoryCb,
    MenuCb,
    ServiceAdminCb,
    SlotAdminCb,
)
from keyboards.inline import (
    build_calendar_keyboard,
    get_admin_appointments_kb,
    get_admin_category_kb,
    get_admin_menu_kb,
    get_admin_price_menu_kb,
    get_admin_services_delete_kb,
    get_admin_slots_delete_kb,
    get_back_menu_kb,
)
from services.scheduler import ReminderScheduler
from states.admin import AdminStates
from utils.default_data import CATEGORY_TITLES
from utils.helpers import human_date
from utils.messages import format_channel_cancellation_notification


router = Router(name="admin")


def is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.ADMIN_IDS


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
async def admin_prices_menu(callback: CallbackQuery, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    await callback.message.edit_text(
        "💰 <b>Управление прайсом</b>\n\nВыберите действие:",
        reply_markup=get_admin_price_menu_kb(),
    )
    await callback.answer()


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
    await open_admin_calendar(callback, "cc", "❌ <b>Отмена записи клиента</b>\n\nВыберите дату:")


@router.callback_query(AdminCb.filter(F.action == "add_service"))
async def admin_add_service(callback: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminStates.choose_service_category)
    await state.update_data(admin_action="add_service")
    await callback.message.edit_text(
        "Выберите категорию для новой услуги:",
        reply_markup=get_admin_category_kb(),
    )
    await callback.answer()


@router.callback_query(AdminCb.filter(F.action == "delete_service"))
async def admin_delete_service_menu(callback: CallbackQuery, config: Config, db: Database) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    services = await db.get_services(only_active=True)
    if not services:
        await callback.message.edit_text(
            "Активных услуг нет.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выберите услугу для удаления из прайса:",
        reply_markup=get_admin_services_delete_kb(services),
    )
    await callback.answer()


@router.callback_query(CalendarCb.filter((F.day == 0) & (F.scope.in_({"ad", "as", "ds", "sd", "cd", "cc"}))))
async def admin_calendar_nav(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
) -> None:
    if callback_data.scope not in {"ad", "as", "ds", "sd", "cd", "cc"}:
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

        try:
            await bot.send_message(
                config.SCHEDULE_CHANNEL_ID,
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


@router.callback_query(CalendarCb.filter((F.scope == "cc") & (F.day > 0)))
async def admin_pick_cancel_client_date(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    selected = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
    appointments = await db.get_appointments_by_date(selected)
    if not appointments:
        await callback.message.edit_text(
            f"На <b>{human_date(selected)}</b> активных записей нет.",
            reply_markup=get_admin_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Выберите запись для отмены на <b>{human_date(selected)}</b>:",
        reply_markup=get_admin_appointments_kb(appointments),
    )
    await callback.answer()


@router.callback_query(StateFilter(AdminStates.choose_service_category), CategoryCb.filter())
async def admin_pick_service_category(
    callback: CallbackQuery,
    callback_data: CategoryCb,
    config: Config,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id, config):
        return

    data = await state.get_data()
    if data.get("admin_action") != "add_service":
        return

    await state.update_data(category=callback_data.category)
    await state.set_state(AdminStates.add_service_name)

    category_title = CATEGORY_TITLES.get(callback_data.category, callback_data.category)
    await callback.message.edit_text(
        f"Категория выбрана: <b>{category_title}</b>\n\n"
        f"Введите название новой услуги:",
        reply_markup=get_back_menu_kb(),
    )
    await callback.answer()


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
        f"✅ Добавлены слоты на <b>{human_date(selected_date)}</b>:\n"
        + ", ".join(valid_times),
        reply_markup=get_admin_menu_kb(),
    )


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
        f"🗑 Услуга <b>{service['name']}</b> удалена из активного прайса.",
        reply_markup=get_admin_menu_kb(),
    )
    await callback.answer()


@router.callback_query(SlotAdminCb.filter(F.action == "delete"))
async def admin_delete_slot(
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

    deleted = await db.disable_time_slot(slot["id"])
    if not deleted:
        await callback.answer("Нельзя удалить занятый слот.", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 Слот <b>{slot['time']}</b> на <b>{human_date(slot['work_date'])}</b> скрыт.",
        reply_markup=get_admin_menu_kb(),
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
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    scheduler.remove_job(appointment.get("reminder_job_id"))
    await db.cancel_appointment(appointment["id"], cancelled_by="admin")
    await db.update_appointment_reminder_job(appointment["id"], None)

    try:
        await bot.send_message(
            appointment["user_id"],
            "❌ <b>Ваша запись была отменена администратором.</b>\n\n"
            f"Дата: {human_date(appointment['work_date'])}\n"
            f"Время: {appointment['time']}\n"
            f"Услуга: {appointment['service_name']}\n"
            "Вы можете выбрать другую дату в боте.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    try:
        await bot.send_message(
            config.SCHEDULE_CHANNEL_ID,
            format_channel_cancellation_notification(appointment),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.message.edit_text(
        f"❌ Запись клиента <b>{appointment['full_name']}</b> отменена.",
        reply_markup=get_admin_menu_kb(),
    )
    await callback.answer()
