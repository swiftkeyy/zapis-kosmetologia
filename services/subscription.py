from __future__ import annotations

import logging

from aiogram import Bot

logger = logging.getLogger(__name__)


async def is_subscribed(bot: Bot, channel_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        logger.info("SUB_CHECK OK: channel_id=%s user_id=%s status=%s", channel_id, user_id, member.status)
        return member.status in {"member", "administrator", "creator"}
    except Exception as e:
        logger.exception("SUB_CHECK ERROR: channel_id=%s user_id=%s error=%r", channel_id, user_id, e)
        return False
