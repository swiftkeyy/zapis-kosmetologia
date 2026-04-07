from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext

from config import Config
from database.db import Database
from keyboards.callbacks import MenuCb
from keyboards.inline import get_back_menu_kb, get_main_menu, get_my_appointment_kb
from utils.messages import format_appointment_html


router = Router(name="start")


async def send_or_edit(target: Message | CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    if isinstance(target, Message):
        await target.answer(text, reply_markup=reply_markup)
    else:
        await target.message.edit_text(text, reply_markup=reply_markup)
        await target.answer()


@router.message(CommandStart())
async def start_command(message: Message, config: Config, state: FSMContext) -> None:
    await state.clear()
    text = (
        "🌷 <b>Добро пожаловать!</b>\n\n"
        "Это бот для записи к <b>Шаеховой Марие</b> "
        "на косметологические услуги и массаж.\n\n"
        "Через меню ниже вы можете:\n"
        "• записаться на свободное время;\n"
        "• посмотреть свою запись;\n"
        "• открыть прайс;\n"
        "• перейти в портфолио."
    )
    await message.answer(
        text,
        reply_markup=get_main_menu(is_admin=message.from_user.id == config.ADMIN_ID),
    )


@router.callback_query(MenuCb.filter(F.action == "main"))
async def show_main_menu(callback: CallbackQuery, config: Config, state: FSMContext) -> None:
    await state.clear()
    text = (
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите нужный раздел."
    )
    await send_or_edit(
        callback,
        text=text,
        reply_markup=get_main_menu(is_admin=callback.from_user.id == config.ADMIN_ID),
    )


@router.callback_query(MenuCb.filter(F.action == "prices"))
async def show_prices(callback: CallbackQuery, db: Database) -> None:
    text = await db.get_price_text_html()
    await send_or_edit(callback, text, get_back_menu_kb())


@router.callback_query(MenuCb.filter(F.action == "portfolio"))
async def show_portfolio(callback: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Смотреть портфолио", url="https://vk.com/kosmetolog_shaekhova")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuCb(action="main").pack())],
        ]
    )
    text = (
        "🖼 <b>Портфолио</b>\n\n"
        "Нажмите на кнопку ниже, чтобы открыть портфолио."
    )
    await send_or_edit(callback, text, kb)


@router.callback_query(MenuCb.filter(F.action == "my"))
async def show_my_appointment(callback: CallbackQuery, db: Database) -> None:
    appointment = await db.get_active_appointment_by_user(callback.from_user.id)
    if not appointment:
        await callback.message.edit_text(
            "У вас сейчас нет активной записи.",
            reply_markup=get_back_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        format_appointment_html(appointment),
        reply_markup=get_my_appointment_kb(appointment["id"]),
    )
    await callback.answer()


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery) -> None:
    await callback.answer()
