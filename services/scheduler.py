from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.db import Database


class ReminderScheduler:
    """Планировщик напоминаний."""

    def __init__(self, bot: Bot, db: Database, timezone: str) -> None:
        self.bot = bot
        self.db = db
        self.timezone = ZoneInfo(timezone)
        self.scheduler = AsyncIOScheduler(timezone=self.timezone)

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def send_reminder(self, user_id: int, appointment_time: str) -> None:
        template = await self.db.get_setting(
            "reminder_text",
            "⏰ <b>Напоминание</b>\n\nНапоминаем, что вы записаны завтра к Шаеховой Марие в <b>{time}</b>.\nЖдём вас ❤️",
        )
        try:
            text = template.format(time=appointment_time)
        except Exception:
            text = template
        try:
            await self.bot.send_message(user_id, text, parse_mode="HTML")
        except Exception:
            pass

    async def schedule_appointment_reminder(self, appointment_id: int) -> str | None:
        appointment = await self.db.get_appointment(appointment_id)
        if not appointment or appointment["status"] != "booked":
            return None

        visit_dt = datetime.strptime(
            f"{appointment['work_date']} {appointment['time']}",
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=self.timezone)

        now = datetime.now(self.timezone)
        reminder_dt = visit_dt - timedelta(hours=24)

        if reminder_dt <= now:
            await self.db.update_appointment_reminder_job(appointment_id, None)
            return None

        job_id = f"appointment_reminder_{appointment_id}"
        self.scheduler.add_job(
            self.send_reminder,
            trigger="date",
            run_date=reminder_dt,
            args=[appointment["user_id"], appointment["time"]],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600,
        )
        await self.db.update_appointment_reminder_job(appointment_id, job_id)
        return job_id

    def remove_job(self, job_id: str | None) -> None:
        if not job_id:
            return
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.remove_job(job_id)

    async def restore_jobs(self) -> None:
        appointments = await self.db.get_future_active_appointments()
        for appointment in appointments:
            await self.schedule_appointment_reminder(appointment["id"])
