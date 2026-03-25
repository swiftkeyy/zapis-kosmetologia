from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database.db import Database
from keyboards.callbacks import CalendarCb, CategoryCb, ConfirmCb, MenuCb, ServiceCb, SlotCb, SubscriptionCb
from keyboards.inline import (
    build_calendar_keyboard,
    get_back_menu_kb,
    get_booking_confirm_kb,
    get_categories_kb,
    get_confirm_cancel_kb,
    get_slots_kb,
    get_subscription_kb,
    get_services_kb,
)
from services.scheduler import ReminderScheduler
from services.subscription import is_subscribed
from states.booking import BookingStates
from utils.default_data import CATEGORY_TITLES
from utils.helpers import human_date, normalize_phone, validate_phone
from utils.messages import (
    format_admin_appointment_notification,
    format_appointment_html,
    format_channel_cancellation_notification,
    format_channel_booking_notification,
)


router = Router(name="booking")


async def open_booking_calendar(
    callback: CallbackQuery,
    db: Database,
) -> None:
    available_dates = await db.get_available_dates(days_ahead=31)
    enabled_dates = {datetime.strptime(item, "%Y-%m-%d").date() for item in available_dates}

    if not enabled_dates:
        await callback.message.edit_text(
            "Сейчас нет свободных дат для записи на ближайший месяц.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    today = date.today()
    max_date = today + timedelta(days=31)
    start_month = today.month
    start_year = today.year

    await callback.message.edit_text(
        "🗓 <b>Выберите дату</b>\n\n"
        "Доступны только свободные дни на ближайший месяц.",
        reply_markup=build_calendar_keyboard(
            scope="usr",
            year=start_year,
            month=start_month,
            enabled_dates=enabled_dates,
            min_date=today,
            max_date=max_date,
        ),
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.action == "book"))
async def start_booking(
    callback: CallbackQuery,
    bot: Bot,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    await state.clear()

    active = await db.get_active_appointment_by_user(callback.from_user.id)
    if active:
        await callback.message.edit_text(
            "У вас уже есть активная запись.\n\n"
            "Сначала отмените текущую запись, чтобы выбрать новую.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    subscribed = await is_subscribed(bot, config.SUBSCRIBE_CHANNEL_ID, callback.from_user.id)
    if not subscribed:
        await callback.message.edit_text(
            "Для записи необходимо подписаться на канал.",
            reply_markup=get_subscription_kb(config.SUBSCRIBE_CHANNEL_LINK),
        )
        await callback.answer()
        return

    await state.set_state(BookingStates.choosing_date)
    await open_booking_calendar(callback, db)


@router.callback_query(SubscriptionCb.filter(F.action == "check"))
async def check_subscription_callback(
    callback: CallbackQuery,
    bot: Bot,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    subscribed = await is_subscribed(bot, config.SUBSCRIBE_CHANNEL_ID, callback.from_user.id)
    if not subscribed:
        await callback.answer("Подписка пока не подтверждена.", show_alert=True)
        return

    active = await db.get_active_appointment_by_user(callback.from_user.id)
    if active:
        await callback.message.edit_text(
            "У вас уже есть активная запись. Сначала отмените её, чтобы выбрать новую дату.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(BookingStates.choosing_date)
    await open_booking_calendar(callback, db)


@router.callback_query(CalendarCb.filter((F.scope == "usr") & (F.day == 0)))
async def booking_calendar_nav(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    db: Database,
) -> None:
    available_dates = await db.get_available_dates(days_ahead=31)
    enabled_dates = {datetime.strptime(item, "%Y-%m-%d").date() for item in available_dates}
    today = date.today()
    max_date = today + timedelta(days=31)

    await callback.message.edit_reply_markup(
        reply_markup=build_calendar_keyboard(
            scope="usr",
            year=callback_data.year,
            month=callback_data.month,
            enabled_dates=enabled_dates,
            min_date=today,
            max_date=max_date,
        )
    )
    await callback.answer()


@router.callback_query(CalendarCb.filter((F.scope == "usr") & (F.day > 0)))
async def booking_choose_date(
    callback: CallbackQuery,
    callback_data: CalendarCb,
    state: FSMContext,
) -> None:
    selected = date(callback_data.year, callback_data.month, callback_data.day)
    await state.update_data(selected_date=selected.isoformat())
    await state.set_state(BookingStates.choosing_category)

    await callback.message.edit_text(
        f"📅 <b>Дата:</b> {human_date(selected.isoformat())}\n\n"
        f"Теперь выберите направление услуги:",
        reply_markup=get_categories_kb(),
    )
    await callback.answer()


@router.callback_query(StateFilter(BookingStates.choosing_category, BookingStates.choosing_service), CategoryCb.filter())
async def booking_choose_category(
    callback: CallbackQuery,
    callback_data: CategoryCb,
    state: FSMContext,
    db: Database,
) -> None:
    current_state = await state.get_state()
    if current_state not in {BookingStates.choosing_category.state, BookingStates.choosing_service.state}:
        return

    services = await db.get_services_by_category(callback_data.category)
    if not services:
        await callback.answer("В этой категории пока нет активных услуг.", show_alert=True)
        return

    await state.update_data(category=callback_data.category)
    await state.set_state(BookingStates.choosing_service)

    title = CATEGORY_TITLES.get(callback_data.category, callback_data.category)
    await callback.message.edit_text(
        f"<b>{title}</b>\n\nВыберите услугу:",
        reply_markup=get_services_kb(services),
    )
    await callback.answer()


@router.callback_query(ServiceCb.filter())
async def booking_choose_service(
    callback: CallbackQuery,
    callback_data: ServiceCb,
    state: FSMContext,
    db: Database,
) -> None:
    service = await db.get_service(callback_data.service_id)
    data = await state.get_data()
    selected_date = data.get("selected_date")
    if not service or not selected_date:
        await callback.answer("Не удалось продолжить запись.", show_alert=True)
        return

    slots = await db.get_available_slots(selected_date)
    if not slots:
        await callback.message.edit_text(
            "На выбранную дату свободного времени больше нет.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    await state.update_data(service_id=service["id"])
    await state.set_state(BookingStates.choosing_slot)

    await callback.message.edit_text(
        f"📅 <b>Дата:</b> {human_date(selected_date)}\n"
        f"💼 <b>Услуга:</b> {service['name']}\n\n"
        f"Выберите свободное время:",
        reply_markup=get_slots_kb(slots),
    )
    await callback.answer()


@router.callback_query(SlotCb.filter())
async def booking_choose_slot(
    callback: CallbackQuery,
    callback_data: SlotCb,
    state: FSMContext,
    db: Database,
) -> None:
    slot = await db.get_slot(callback_data.slot_id)
    if not slot or not slot["is_active"] or slot["is_closed"]:
        await callback.answer("Этот слот недоступен.", show_alert=True)
        return

    available_slots = await db.get_available_slots(slot["work_date"])
    if not any(item["id"] == slot["id"] for item in available_slots):
        await callback.answer("К сожалению, этот слот уже занят.", show_alert=True)
        return

    await state.update_data(slot_id=slot["id"])
    await state.set_state(BookingStates.waiting_name)

    await callback.message.edit_text(
        f"🕒 Вы выбрали <b>{slot['time']}</b> на <b>{human_date(slot['work_date'])}</b>.\n\n"
        f"Введите ваше <b>имя</b>:",
        reply_markup=get_back_menu_kb(),
    )
    await callback.answer()


@router.message(BookingStates.waiting_name)
async def booking_get_name(message: Message, state: FSMContext) -> None:
    full_name = message.text.strip()
    if len(full_name) < 2:
        await message.answer("Пожалуйста, введите корректное имя.")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(BookingStates.waiting_phone)
    await message.answer(
        "Теперь отправьте <b>номер телефона</b>.\n"
        "Пример: <code>+79991234567</code>",
        reply_markup=get_back_menu_kb(),
    )


@router.message(BookingStates.waiting_phone)
async def booking_get_phone(message: Message, state: FSMContext, db: Database) -> None:
    raw_phone = message.text.strip()
    if not validate_phone(raw_phone):
        await message.answer(
            "Введите корректный номер телефона.\n"
            "Подойдут форматы <code>+79991234567</code> или <code>89991234567</code>."
        )
        return

    phone = normalize_phone(raw_phone)
    data = await state.get_data()

    service = await db.get_service(int(data["service_id"]))
    slot = await db.get_slot(int(data["slot_id"]))
    if not service or not slot:
        await state.clear()
        await message.answer(
            "Не удалось завершить запись. Попробуйте заново.",
            reply_markup=get_back_menu_kb(),
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(BookingStates.confirming)

    summary = (
        "<b>Проверьте данные записи</b>\n\n"
        f"<b>Дата:</b> {human_date(slot['work_date'])}\n"
        f"<b>Время:</b> {slot['time']}\n"
        f"<b>Услуга:</b> {service['name']}\n"
        f"<b>Стоимость:</b> {service['price']}₽\n"
        f"<b>Имя:</b> {data['full_name']}\n"
        f"<b>Телефон:</b> {phone}"
    )

    await message.answer(summary, reply_markup=get_booking_confirm_kb())


@router.callback_query(MenuCb.filter(F.action == "confirm_booking"))
async def booking_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    scheduler: ReminderScheduler,
    bot: Bot,
    config: Config,
) -> None:
    data = await state.get_data()
    required_fields = {"slot_id", "service_id", "full_name", "phone"}
    if not required_fields.issubset(data):
        await callback.answer("Недостаточно данных для записи.", show_alert=True)
        return

    existing = await db.get_active_appointment_by_user(callback.from_user.id)
    if existing:
        await state.clear()
        await callback.message.edit_text(
            "У вас уже есть активная запись.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    slot = await db.get_slot(int(data["slot_id"]))
    if not slot:
        await state.clear()
        await callback.message.edit_text(
            "Слот не найден.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    available_slots = await db.get_available_slots(slot["work_date"])
    if not any(item["id"] == slot["id"] for item in available_slots):
        await state.clear()
        await callback.message.edit_text(
            "К сожалению, выбранное время уже занято. Попробуйте записаться ещё раз.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    try:
        appointment_id = await db.create_appointment(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=data["full_name"],
            phone=data["phone"],
            service_id=int(data["service_id"]),
            slot_id=int(data["slot_id"]),
        )
    except sqlite3.IntegrityError:
        await state.clear()
        await callback.message.edit_text(
            "Не удалось создать запись: время уже занято или у вас уже есть активная запись.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    await scheduler.schedule_appointment_reminder(appointment_id)
    appointment = await db.get_appointment(appointment_id)
    await state.clear()

    if appointment:
        # Уведомление владельцу бота
        for admin_id in config.ADMIN_IDS:
    try:
        await bot.send_message(
            admin_id,
            format_admin_appointment_notification(appointment),
            parse_mode="HTML",
        )
    except Exception:
        pass

        # Уведомление в канал с расписанием
        try:
            await bot.send_message(
                config.SCHEDULE_CHANNEL_ID,
                format_channel_booking_notification(appointment),
                parse_mode="HTML",
            )
        except Exception:
            pass

        await callback.message.edit_text(
            "✅ <b>Запись успешно создана!</b>\n\n"
            + format_appointment_html(appointment),
            reply_markup=get_back_menu_kb(),
        )
    else:
        await callback.message.edit_text(
            "✅ Запись создана.",
            reply_markup=get_back_menu_kb(),
        )

    await callback.answer("Готово!")


@router.callback_query(ConfirmCb.filter(F.action == "cancel_my"))
async def ask_cancel_my_booking(callback: CallbackQuery, callback_data: ConfirmCb, db: Database) -> None:
    appointment = await db.get_appointment(callback_data.entity_id)
    if not appointment or appointment["user_id"] != callback.from_user.id:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    await callback.message.edit_text(
        "Вы уверены, что хотите отменить запись?",
        reply_markup=get_confirm_cancel_kb(appointment["id"]),
    )
    await callback.answer()


@router.callback_query(ConfirmCb.filter(F.action == "cancel_yes"))
async def cancel_my_booking(
    callback: CallbackQuery,
    callback_data: ConfirmCb,
    db: Database,
    scheduler: ReminderScheduler,
    bot: Bot,
    config: Config,
) -> None:
    appointment = await db.get_appointment(callback_data.entity_id)
    if not appointment or appointment["user_id"] != callback.from_user.id or appointment["status"] != "booked":
        await callback.answer("Активная запись не найдена.", show_alert=True)
        return

    scheduler.remove_job(appointment.get("reminder_job_id"))
    await db.cancel_appointment(appointment["id"], cancelled_by="user")
    await db.update_appointment_reminder_job(appointment["id"], None)

    for admin_id in config.ADMIN_IDS:
    try:
        await bot.send_message(
            admin_id,
            "❌ <b>Клиент отменил запись</b>\n\n" + format_appointment_html(appointment),
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
        "Ваша запись отменена. Слот снова стал доступен для бронирования.",
        reply_markup=get_back_menu_kb(),
    )
    await callback.answer()
