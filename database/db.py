from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from utils.default_data import CATEGORY_TITLES, DEFAULT_SERVICES


DEFAULT_TEXT_SETTINGS: dict[str, str] = {
    "welcome_text": (
        "🌷 <b>Добро пожаловать!</b>\n\n"
        "Это бот для записи к <b>Шаеховой Марие</b> "
        "на косметологические услуги и массаж.\n\n"
        "Через меню ниже вы можете:\n"
        "• записаться на свободное время;\n"
        "• посмотреть свою запись;\n"
        "• открыть прайс;\n"
        "• перейти в портфолио."
    ),
    "subscription_required_text": "Для записи необходимо подписаться на канал.",
    "subscription_failed_text": "Подписка пока не подтверждена.",
    "reminder_text": (
        "⏰ <b>Напоминание</b>\n\n"
        "Напоминаем, что вы записаны завтра к Шаеховой Марие в <b>{time}</b>.\n"
        "Ждём вас ❤️"
    ),
}


class Database:
    """Асинхронный слой работы с SQLite."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._ensure_db_directory()

    def _ensure_db_directory(self) -> None:
        db_path = Path(self.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def _connect(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.execute("PRAGMA journal_mode = WAL;")
            await db.execute("PRAGMA synchronous = NORMAL;")
            await db.execute("PRAGMA busy_timeout = 5000;")
            yield db

    async def init(self) -> None:
        self._ensure_db_directory()
        async with self._connect() as db:

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
                CREATE TABLE IF NOT EXISTS clients (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        await self.seed_text_settings()
        await self.backfill_clients()

    async def _fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        async with self._connect() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def _fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        async with self._connect() as db:
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def _execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        async with self._connect() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.lastrowid

    async def seed_services(self) -> None:
        exists = await self._fetchone("SELECT id FROM services LIMIT 1")
        if exists:
            return

        async with self._connect() as db:
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

    async def seed_text_settings(self) -> None:
        async with self._connect() as db:
            for key, value in DEFAULT_TEXT_SETTINGS.items():
                await db.execute(
                    """
                    INSERT INTO settings(key, value)
                    VALUES(?, ?)
                    ON CONFLICT(key) DO NOTHING
                    """,
                    (key, value),
                )
            await db.commit()

    async def backfill_clients(self) -> None:
        rows = await self._fetchall(
            """
            SELECT
                a.user_id,
                COALESCE(MAX(a.username), '') AS username,
                COALESCE(MAX(a.full_name), '') AS full_name,
                COALESCE(MAX(a.phone), '') AS phone
            FROM appointments a
            GROUP BY a.user_id
            """
        )
        async with self._connect() as db:
            for row in rows:
                await db.execute(
                    """
                    INSERT INTO clients(user_id, username, full_name, phone)
                    VALUES(?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        full_name = excluded.full_name,
                        phone = excluded.phone,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (row["user_id"], row["username"], row["full_name"], row["phone"]),
                )
            await db.commit()

    async def upsert_client(self, user_id: int, username: str | None, full_name: str, phone: str) -> None:
        async with self._connect() as db:
            await db.execute(
                """
                INSERT INTO clients(user_id, username, full_name, phone)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    phone = excluded.phone,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, username or "", full_name, phone),
            )
            await db.commit()

    async def get_setting(self, key: str, default: str = "") -> str:
        row = await self._fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        if not row:
            return default
        return row["value"]

    async def set_setting(self, key: str, value: str) -> None:
        await self._execute(
            """
            INSERT INTO settings(key, value, updated_at)
            VALUES(?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )

    async def get_text_settings(self) -> dict[str, str]:
        data = dict(DEFAULT_TEXT_SETTINGS)
        rows = await self._fetchall("SELECT key, value FROM settings")
        for row in rows:
            data[row["key"]] = row["value"]
        return data

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
        async with self._connect() as db:
            await db.execute(
                """
                INSERT INTO work_days(date, is_closed)
                VALUES(?, 0)
                ON CONFLICT(date) DO UPDATE SET is_closed = 0
                """,
                (day,),
            )
            await db.commit()

    async def add_work_days_range(self, start_day: str, end_day: str) -> int:
        start = date.fromisoformat(start_day)
        end = date.fromisoformat(end_day)
        if end < start:
            start, end = end, start
        count = 0
        current = start
        while current <= end:
            await self.add_work_day(current.isoformat())
            count += 1
            current += timedelta(days=1)
        return count

    async def set_day_closed(self, day: str, is_closed: bool = True) -> None:
        await self.add_work_day(day)
        await self._execute(
            "UPDATE work_days SET is_closed = ? WHERE date = ?",
            (1 if is_closed else 0, day),
        )

    async def set_day_closed_range(self, start_day: str, end_day: str, is_closed: bool) -> int:
        start = date.fromisoformat(start_day)
        end = date.fromisoformat(end_day)
        if end < start:
            start, end = end, start
        count = 0
        current = start
        while current <= end:
            await self.set_day_closed(current.isoformat(), is_closed=is_closed)
            count += 1
            current += timedelta(days=1)
        return count

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
        appointment_id = await self._execute(
            """
            INSERT INTO appointments(user_id, username, full_name, phone, service_id, slot_id, status)
            VALUES(?, ?, ?, ?, ?, ?, 'booked')
            """,
            (user_id, username, full_name, phone, service_id, slot_id),
        )
        await self.upsert_client(user_id, username, full_name, phone)
        return appointment_id

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
        async with self._connect() as db:
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

    async def search_clients(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        pattern = f"%{query.strip()}%"
        return await self._fetchall(
            """
            SELECT
                c.user_id,
                c.full_name,
                c.phone,
                c.username,
                c.is_blocked,
                COALESCE(SUM(CASE WHEN a.status = 'booked' THEN 1 ELSE 0 END), 0) AS active_count,
                COALESCE(COUNT(a.id), 0) AS total_visits
            FROM clients c
            LEFT JOIN appointments a ON a.user_id = c.user_id
            WHERE CAST(c.user_id AS TEXT) LIKE ?
               OR COALESCE(c.full_name, '') LIKE ?
               OR COALESCE(c.phone, '') LIKE ?
               OR COALESCE(c.username, '') LIKE ?
            GROUP BY c.user_id, c.full_name, c.phone, c.username, c.is_blocked
            ORDER BY c.is_blocked DESC, total_visits DESC, c.full_name
            LIMIT ?
            """,
            (pattern, pattern, pattern, pattern, limit),
        )

    async def get_client_profile(self, user_id: int) -> dict[str, Any] | None:
        return await self._fetchone(
            """
            SELECT
                c.user_id,
                c.full_name,
                c.phone,
                c.username,
                c.note,
                c.is_blocked,
                COALESCE(SUM(CASE WHEN a.status = 'booked' THEN 1 ELSE 0 END), 0) AS active_count,
                COALESCE(SUM(CASE WHEN a.status = 'cancelled' THEN 1 ELSE 0 END), 0) AS cancelled_count,
                COALESCE(COUNT(a.id), 0) AS total_visits,
                MAX(a.created_at) AS last_created_at
            FROM clients c
            LEFT JOIN appointments a ON a.user_id = c.user_id
            WHERE c.user_id = ?
            GROUP BY c.user_id, c.full_name, c.phone, c.username, c.note, c.is_blocked
            """,
            (user_id,),
        )

    async def get_client_history(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        return await self._fetchall(
            """
            SELECT
                a.id,
                a.status,
                a.created_at,
                a.cancelled_at,
                a.cancelled_by,
                ts.work_date,
                ts.time,
                s.name AS service_name,
                s.category,
                s.price
            FROM appointments a
            JOIN time_slots ts ON ts.id = a.slot_id
            JOIN services s ON s.id = a.service_id
            WHERE a.user_id = ?
            ORDER BY ts.work_date DESC, ts.time DESC
            LIMIT ?
            """,
            (user_id, limit),
        )

    async def set_client_blocked(self, user_id: int, is_blocked: bool) -> None:
        await self._execute(
            "UPDATE clients SET is_blocked = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (1 if is_blocked else 0, user_id),
        )

    async def is_client_blocked(self, user_id: int) -> bool:
        row = await self._fetchone("SELECT is_blocked FROM clients WHERE user_id = ?", (user_id,))
        return bool(row and row["is_blocked"])

    async def get_blocked_clients(self) -> list[dict[str, Any]]:
        return await self._fetchall(
            """
            SELECT user_id, full_name, phone, username, is_blocked
            FROM clients
            WHERE is_blocked = 1
            ORDER BY full_name, user_id
            """
        )

    async def add_time_slots_bulk(self, day: str, times: list[str]) -> list[str]:
        saved: list[str] = []
        for time_value in times:
            await self.add_time_slot(day, time_value)
            saved.append(time_value)
        return saved

    async def copy_schedule_to_date(self, source_date: str, target_date: str) -> dict[str, int | bool]:
        source_work_day = await self.get_work_day(source_date)
        if not source_work_day:
            return {"copied": 0, "skipped": 0, "target_closed": False}

        source_slots = await self._fetchall(
            """
            SELECT time, is_active
            FROM time_slots
            WHERE work_date = ?
            ORDER BY time
            """,
            (source_date,),
        )

        await self.add_work_day(target_date)
        await self.set_day_closed(target_date, bool(source_work_day["is_closed"]))

        copied = 0
        skipped = 0
        async with self._connect() as db:
            for slot in source_slots:
                cursor = await db.execute(
                    """
                    INSERT INTO time_slots(work_date, time, is_active)
                    VALUES(?, ?, ?)
                    ON CONFLICT(work_date, time) DO NOTHING
                    """,
                    (target_date, slot["time"], slot["is_active"]),
                )
                if cursor.rowcount and cursor.rowcount > 0:
                    copied += 1
                else:
                    skipped += 1
            await db.commit()

        return {
            "copied": copied,
            "skipped": skipped,
            "target_closed": bool(source_work_day["is_closed"]),
        }

    async def get_stats_between(self, start_day: str, end_day: str) -> dict[str, Any]:
        summary = await self._fetchone(
            """
            SELECT
                COUNT(a.id) AS total,
                COALESCE(SUM(CASE WHEN a.status = 'booked' THEN 1 ELSE 0 END), 0) AS booked_count,
                COALESCE(SUM(CASE WHEN a.status = 'cancelled' THEN 1 ELSE 0 END), 0) AS cancelled_count,
                COALESCE(SUM(CASE WHEN a.status = 'booked' THEN s.price ELSE 0 END), 0) AS booked_revenue
            FROM appointments a
            JOIN time_slots ts ON ts.id = a.slot_id
            JOIN services s ON s.id = a.service_id
            WHERE ts.work_date >= ? AND ts.work_date <= ?
            """,
            (start_day, end_day),
        ) or {"total": 0, "booked_count": 0, "cancelled_count": 0, "booked_revenue": 0}

        popular_services = await self._fetchall(
            """
            SELECT s.name, COUNT(a.id) AS qty
            FROM appointments a
            JOIN time_slots ts ON ts.id = a.slot_id
            JOIN services s ON s.id = a.service_id
            WHERE ts.work_date >= ? AND ts.work_date <= ?
            GROUP BY s.id, s.name
            ORDER BY qty DESC, s.name
            LIMIT 5
            """,
            (start_day, end_day),
        )

        free_tomorrow = await self._fetchone(
            """
            SELECT COUNT(ts.id) AS cnt
            FROM time_slots ts
            JOIN work_days wd ON wd.date = ts.work_date
            LEFT JOIN appointments a ON a.slot_id = ts.id AND a.status = 'booked'
            WHERE ts.work_date = ?
              AND ts.is_active = 1
              AND wd.is_closed = 0
              AND a.id IS NULL
            """,
            ((date.today() + timedelta(days=1)).isoformat(),),
        )

        blocked = await self._fetchone("SELECT COUNT(*) AS cnt FROM clients WHERE is_blocked = 1")

        summary["popular_services"] = popular_services
        summary["free_tomorrow"] = int((free_tomorrow or {"cnt": 0})["cnt"])
        summary["blocked_clients"] = int((blocked or {"cnt": 0})["cnt"])
        return summary

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
