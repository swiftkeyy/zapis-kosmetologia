from __future__ import annotations

from aiogram import Bot


async def is_subscribed(bot: Bot, channel_id: int, user_id: int) -> bool:
    """
    Проверяет подписку пользователя на канал.
    Бот должен быть добавлен в канал/группу и иметь право читать участников.
    """
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status not in {"left", "kicked"}
    except Exception:
        return False
