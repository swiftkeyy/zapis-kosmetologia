from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from config import Config
from keyboards.inline import get_main_menu
from utils.messages import START_TEXT

router = Router()


def is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(CommandStart())
async def start_command(message: Message, config: Config) -> None:
    await message.answer(
        START_TEXT,
        reply_markup=get_main_menu(is_admin=is_admin(message.from_user.id, config)),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, config: Config) -> None:
    await callback.message.edit_text(
        START_TEXT,
        reply_markup=get_main_menu(is_admin=is_admin(callback.from_user.id, config)),
        parse_mode="HTML",
    )
    await callback.answer()
