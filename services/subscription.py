from __future__ import annotations

from aiogram import Bot


async def is_subscribed(bot, channel_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        print("CHECK SUB:", channel_id, user_id, member.status)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        print("SUB CHECK ERROR:", repr(e))
        return False
