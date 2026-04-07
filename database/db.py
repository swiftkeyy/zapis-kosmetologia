from __future__ import annotations

import aiosqlite
from typing import Any

from utils.default_data import CATEGORY_TITLES, DEFAULT_SERVICES


class Database:
    """Асинхронный слой работы с SQLite."""

    def __init__(self, path: str) -> None:
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON;")

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('massage', 'cosmetology')),
                    price INTEGER NOT NULL,
                    description TEXT DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS work_days (
                    date TEXT PRIMARY KEY,
                    is_closed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS time_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(work_date) REFERENCES work_days(date) ON DELETE CASCADE,
                    UNIQUE(work_date, time)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    service_id INTEGER NOT NULL,
                    slot_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'booked',
                    reminder_job_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    cancelled_at TEXT,
                    cancelled_by TEXT,
                    FOREIGN KEY(service_id) REFERENCES services(id),
                    FOREIGN KEY(slot_id) REFERENCES time_slots(id)
                )
                """
            )

            await db.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_user
                ON appointments(user_id)
                WHERE status = 'booked'
                """
            )

            await db.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_slot
                ON appointments(slot_id)
                WHERE status = 'booked'
                """
            )

            await db.commit()

        await self.seed_services()

    async def _fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def _fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def _execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.lastrowid

    async def seed_services(self) -> None:
        exists = await self._fetchone("SELECT id FROM services LIMIT 1")
        if exists:
            return

        async with aiosqlite.connect(self.path) as db:
            for service in DEFAULT_SERVICES:
                await db.execute(
                    """
                    INSERT INTO services(name, category, price, description, is_active)
                    VALUES(?, ?, ?, ?, 1)
                    """,
                    (
                        service["name"],
                        service["category"],
                        service["price"],
                        service["description"],
                    ),
                )
            await db.commit()

    async def get_services(self, only_active: bool = True) -> list[dict[str, Any]]:
        query = """
            SELECT id, name, category, price, description, is_active
            FROM services
        """
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY category, id"
        return await self._fetchall(query)

    async def get_services_by_category(self, category: str) -> list[dict[str, Any]]:
        return await self._fetchall(
            """
            SELECT id, name, category, price, description
            FROM services
            WHERE category = ? AND is_active = 1
            ORDER BY id
            """,
            (category,),
        )

    async def get_services_for_admin(self, category: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT id, name, category, price, description, is_active
            FROM services
        """
        params: tuple[Any, ...] = ()
        if category:
            query += " WHERE category = ?"
            params = (category,)
        query += " ORDER BY category, is_active DESC, id"
        return await self._fetchall(query, params)

    async def get_service(self, service_id: int) -> dict[str, Any] | None:
        service = await self._fetchone(
            """
            SELECT id, name, category, price, description, is_active
            FROM services
            WHERE id = ?
            """,
            (service_id,),
        )
        if service:
            service["category_title"] = CATEGORY_TITLES.get(service["category"], service["category"])
        return service

    async def add_service(self, name: str, category: str, price: int, description: str = "") -> int:
        return await self._execute(
            """
            INSERT INTO services(name, category, price, description, is_active)
            VALUES(?, ?, ?, ?, 1)
            """,
            (name, category, price, description),
        )

    async def update_service_name(self, service_id: int, name: str) -> None:
        await self._execute("UPDATE services SET name = ? WHERE id = ?", (name, service_id))

    async def update_service_price(self, service_id: int, price: int) -> None:
        await self._execute("UPDATE services SET price = ? WHERE id = ?", (price, service_id))

    async def set_service_active(self, service_id: int, is_active: bool) -> None:
        await self._execute("UPDATE services SET is_active = ? WHERE id = ?", (1 if is_active else 0, service_id))

    async def disable_service(self, service_id: int) -> None:
        await self.set_service_active(service_id, False)

    async def add_work_day(self, day: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO work_days(date, is_closed)
                VALUES(?, 0)
                ON CONFLICT(date) DO UPDATE SET is_closed = 0
                """,
                (day,),
            )
            await db.commit()

    async def set_day_closed(self, day: str, is_closed: bool = True) -> None:
        await self.add_work_day(day)
        await self._execute(
            "UPDATE work_days SET is_closed = ? WHERE date = ?",
            (1 if is_closed else 0, day),
        )

    async def get_work_day(self, day: str) -> dict[str, Any] | None:
        return await self._fetchone(
            "SELECT date, is_closed FROM work_days WHERE date = ?",
            (day,),
        )

    async def add_time_slot(self, day: str, time_value: str) -> int:
        await self.add_work_day(day)
        return await self._execute(
            """
            INSERT INTO time_slots(work_date, time, is_active)
            VALUES(?, ?, 1)
            ON CONFLICT(work_date, time) DO UPDATE SET is_active = 1
            """,
            (day, time_value),
        )

    async def disable_time_slot(self, slot_id: int) -> bool:
        booked = await self._fetchone(
            """
            SELECT id FROM appointments
            WHERE slot_id = ? AND status = 'booked'
            """,
            (slot_id,),
        )
        if booked:
            return False

        await self._execute(
            "UPDATE time_slots SET is_active = 0 WHERE id = ?",
            (slot_id,),
        )
        return True

    async def get_available_dates(self, days_ahead: int = 31) -> list[str]:
        from datetime import date, timedelta

        start_date = date.today().isoformat()
        end_date = (date.today() + timedelta(days=days_ahead)).isoformat()
        return [
            row["date"]
            for row in await self._fetchall(
                """
                SELECT DISTINCT wd.date AS date
                FROM work_days wd
                JOIN time_slots ts ON ts.work_date = wd.date AND ts.is_active = 1
                LEFT JOIN appointments a ON a.slot_id = ts.id AND a.status = 'booked'
                WHERE wd.is_closed = 0
                  AND a.id IS NULL
                  AND date(wd.date) >= date(?)
                  AND date(wd.date) <= date(?)
                ORDER BY wd.date
                """,
                (start_date, end_date),
            )
        ]

    async def get_available_slots(self, day: str) -> list[dict[str, Any]]:
        return await self._fetchall(
            """
            SELECT ts.id, ts.work_date, ts.time
            FROM time_slots ts
            JOIN work_days wd ON wd.date = ts.work_date
            LEFT JOIN appointments a ON a.slot_id = ts.id AND a.status = 'booked'
            WHERE ts.work_date = ?
              AND ts.is_active = 1
              AND wd.is_closed = 0
              AND a.id IS NULL
            ORDER BY ts.time
            """,
            (day,),
        )

    async def get_all_slots_for_admin(self, day: str) -> list[dict[str, Any]]:
        return await self._fetchall(
            """
            SELECT
                ts.id,
                ts.work_date,
                ts.time,
                ts.is_active,
                CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END AS is_booked,
                a.full_name,
                a.phone,
                s.name AS service_name
            FROM time_slots ts
            LEFT JOIN appointments a ON a.slot_id = ts.id AND a.status = 'booked'
            LEFT JOIN services s ON s.id = a.service_id
            WHERE ts.work_date = ?
            ORDER BY ts.time
            """,
            (day,),
        )

    async def get_slot(self, slot_id: int) -> dict[str, Any] | None:
        return await self._fetchone(
            """
            SELECT ts.id, ts.work_date, ts.time, ts.is_active, wd.is_closed
            FROM time_slots ts
            JOIN work_days wd ON wd.date = ts.work_date
            WHERE ts.id = ?
            """,
            (slot_id,),
        )

    async def get_active_appointment_by_user(self, user_id: int) -> dict[str, Any] | None:
        return await self._fetchone(
            """
            SELECT
                a.id,
                a.user_id,
                a.username,
                a.full_name,
                a.phone,
                a.status,
                a.reminder_job_id,
                ts.id AS slot_id,
                ts.work_date,
                ts.time,
                s.id AS service_id,
                s.name AS service_name,
                s.category,
                s.price
            FROM appointments a
            JOIN time_slots ts ON ts.id = a.slot_id
            JOIN services s ON s.id = a.service_id
            WHERE a.user_id = ? AND a.status = 'booked'
            """,
            (user_id,),
        )

    async def create_appointment(
        self,
        user_id: int,
        username: str | None,
        full_name: str,
        phone: str,
        service_id: int,
        slot_id: int,
    ) -> int:
        return await self._execute(
            """
            INSERT INTO appointments(user_id, username, full_name, phone, service_id, slot_id, status)
            VALUES(?, ?, ?, ?, ?, ?, 'booked')
            """,
            (user_id, username, full_name, phone, service_id, slot_id),
        )

    async def get_appointment(self, appointment_id: int) -> dict[str, Any] | None:
        return await self._fetchone(
            """
            SELECT
                a.id,
                a.user_id,
                a.username,
                a.full_name,
                a.phone,
                a.status,
                a.reminder_job_id,
                a.created_at,
                ts.id AS slot_id,
                ts.work_date,
                ts.time,
                s.id AS service_id,
                s.name AS service_name,
                s.category,
                s.price
            FROM appointments a
            JOIN time_slots ts ON ts.id = a.slot_id
            JOIN services s ON s.id = a.service_id
            WHERE a.id = ?
            """,
            (appointment_id,),
        )

    async def cancel_appointment(self, appointment_id: int, cancelled_by: str = "user") -> None:
        await self._execute(
            """
            UPDATE appointments
            SET status = 'cancelled',
                cancelled_at = CURRENT_TIMESTAMP,
                cancelled_by = ?
            WHERE id = ? AND status = 'booked'
            """,
            (cancelled_by, appointment_id),
        )

    async def reschedule_appointment(self, appointment_id: int, new_slot_id: int) -> None:
        await self._execute(
            """
            UPDATE appointments
            SET slot_id = ?,
                reminder_job_id = NULL
            WHERE id = ? AND status = 'booked'
            """,
            (new_slot_id, appointment_id),
        )

    async def update_appointment_reminder_job(self, appointment_id: int, job_id: str | None) -> None:
        await self._execute(
            "UPDATE appointments SET reminder_job_id = ? WHERE id = ?",
            (job_id, appointment_id),
        )

    async def get_appointments_by_date(self, day: str) -> list[dict[str, Any]]:
        return await self._fetchall(
            """
            SELECT
                a.id,
                a.user_id,
                a.username,
                a.full_name,
                a.phone,
                a.status,
                a.reminder_job_id,
                ts.work_date,
                ts.time,
                s.name AS service_name,
                s.category,
                s.price
            FROM appointments a
            JOIN time_slots ts ON ts.id = a.slot_id
            JOIN services s ON s.id = a.service_id
            WHERE ts.work_date = ? AND a.status = 'booked'
            ORDER BY ts.time
            """,
            (day,),
        )

    async def get_future_active_appointments(self) -> list[dict[str, Any]]:
        return await self._fetchall(
            """
            SELECT
                a.id,
                a.user_id,
                a.reminder_job_id,
                ts.work_date,
                ts.time,
                s.name AS service_name
            FROM appointments a
            JOIN time_slots ts ON ts.id = a.slot_id
            JOIN services s ON s.id = a.service_id
            WHERE a.status = 'booked'
              AND datetime(ts.work_date || ' ' || ts.time) > datetime('now', 'localtime')
            ORDER BY ts.work_date, ts.time
            """
        )

    async def get_day_summary(self, day: str) -> dict[str, Any]:
        work_day = await self.get_work_day(day)
        slots = await self.get_all_slots_for_admin(day)
        appointments = await self.get_appointments_by_date(day)
        return {
            "work_day": work_day,
            "slots": slots,
            "appointments": appointments,
        }

    async def close_day_and_cancel_appointments(self, day: str) -> list[dict[str, Any]]:
        appointments = await self.get_appointments_by_date(day)
        await self.set_day_closed(day, True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE appointments
                SET status = 'cancelled',
                    cancelled_at = CURRENT_TIMESTAMP,
                    cancelled_by = 'admin_close_day'
                WHERE id IN (
                    SELECT a.id
                    FROM appointments a
                    JOIN time_slots ts ON ts.id = a.slot_id
                    WHERE ts.work_date = ? AND a.status = 'booked'
                )
                """,
                (day,),
            )
            await db.commit()
        return appointments

    async def get_price_text_html(self) -> str:
        services = await self.get_services(only_active=True)
        massage = [item for item in services if item["category"] == "massage"]
        cosmetology = [item for item in services if item["category"] == "cosmetology"]

        parts: list[str] = ["<b>Прайсы</b>\n"]

        if massage:
            parts.append("<b>Детский массаж и массаж:</b>")
            for service in massage:
                parts.append(f"• {service['name']} — <b>{service['price']}₽</b>")
            parts.append("")

        if cosmetology:
            parts.append("<b>Косметология:</b>")
            for service in cosmetology:
                parts.append(f"• {service['name']} — <b>{service['price']}₽</b>")

        return "\n".join(parts).strip()
