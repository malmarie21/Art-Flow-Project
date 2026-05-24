from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Sequence
from contextlib import asynccontextmanager
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

    @asynccontextmanager
    async def connection(self):
        conn = await asyncio.to_thread(sqlite3.connect, self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            await asyncio.to_thread(conn.commit)
        finally:
            await asyncio.to_thread(conn.close)

    async def execute(self, query: str, params: Sequence | None = None) -> None:
        async with self.connection() as conn:
            await asyncio.to_thread(conn.execute, query, params or [])

    async def fetchone(self, query: str, params: Sequence | None = None):
        async with self.connection() as conn:
            cursor = await asyncio.to_thread(conn.execute, query, params or [])
            return await asyncio.to_thread(cursor.fetchone)

    async def fetchall(self, query: str, params: Sequence | None = None):
        async with self.connection() as conn:
            cursor = await asyncio.to_thread(conn.execute, query, params or [])
            return await asyncio.to_thread(cursor.fetchall)

    async def init(self) -> None:
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                "group" TEXT NOT NULL,
                gender TEXT,
                age_group TEXT,
                art_experience TEXT,
                created_at TEXT NOT NULL,
                lesson_started_at TEXT,
                lesson_completed_at TEXT,
                survey_started_at TEXT,
                survey_completed_at TEXT,
                correct_answers_count INTEGER DEFAULT 0
            )
            """
        )
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                event_value TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                question_number INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                selected_option TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                answer_timestamp TEXT NOT NULL
            )
            """
        )
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS survey_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                survey_question_number INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                selected_option TEXT NOT NULL,
                answered_at TEXT NOT NULL
            )
            """
        )
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS survey_open_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                comment_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    async def get_user(self, telegram_id: int):
        return await self.fetchone(
            'SELECT * FROM users WHERE telegram_id = ?',
            [telegram_id],
        )

    async def get_group_counts(self) -> dict[str, int]:
        rows = await self.fetchall(
            'SELECT "group", COUNT(*) AS count FROM users GROUP BY "group"'
        )
        return {row["group"]: row["count"] for row in rows}

    async def create_user(
        self,
        telegram_id: int,
        username: str | None,
        group: str,
    ) -> None:
        await self.execute(
            """
            INSERT INTO users (telegram_id, username, "group", created_at)
            VALUES (?, ?, ?, ?)
            """,
            [telegram_id, username, group, utc_now_iso()],
        )

    async def update_user_profile(
        self,
        telegram_id: int,
        *,
        gender: str | None = None,
        age_group: str | None = None,
        art_experience: str | None = None,
    ) -> None:
        user = await self.get_user(telegram_id)
        if not user:
            return
        await self.execute(
            """
            UPDATE users
            SET gender = ?, age_group = ?, art_experience = ?
            WHERE telegram_id = ?
            """,
            [
                gender if gender is not None else user["gender"],
                age_group if age_group is not None else user["age_group"],
                art_experience if art_experience is not None else user["art_experience"],
                telegram_id,
            ],
        )

    async def set_lesson_started(self, telegram_id: int) -> None:
        await self.execute(
            'UPDATE users SET lesson_started_at = ? WHERE telegram_id = ?',
            [utc_now_iso(), telegram_id],
        )

    async def set_lesson_completed(self, telegram_id: int, correct_answers_count: int) -> None:
        await self.execute(
            """
            UPDATE users
            SET lesson_completed_at = ?, correct_answers_count = ?
            WHERE telegram_id = ?
            """,
            [utc_now_iso(), correct_answers_count, telegram_id],
        )

    async def set_survey_started(self, telegram_id: int) -> None:
        await self.execute(
            'UPDATE users SET survey_started_at = ? WHERE telegram_id = ?',
            [utc_now_iso(), telegram_id],
        )

    async def set_survey_completed(self, telegram_id: int) -> None:
        await self.execute(
            'UPDATE users SET survey_completed_at = ? WHERE telegram_id = ?',
            [utc_now_iso(), telegram_id],
        )

    async def log_event(self, telegram_id: int, event_name: str, event_value: str | None = None) -> None:
        await self.execute(
            """
            INSERT INTO events (telegram_id, event_name, event_value, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            [telegram_id, event_name, event_value, utc_now_iso()],
        )

    async def save_answer(
        self,
        telegram_id: int,
        question_number: int,
        question_text: str,
        selected_option: str,
        is_correct: bool,
    ) -> None:
        await self.execute(
            """
            INSERT INTO answers (
                telegram_id, question_number, question_text, selected_option, is_correct, answer_timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [telegram_id, question_number, question_text, selected_option, int(is_correct), utc_now_iso()],
        )

    async def save_survey_answer(
        self,
        telegram_id: int,
        question_number: int,
        question_text: str,
        selected_option: str,
    ) -> None:
        await self.execute(
            """
            INSERT INTO survey_answers (
                telegram_id, survey_question_number, question_text, selected_option, answered_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [telegram_id, question_number, question_text, selected_option, utc_now_iso()],
        )

    async def save_survey_open_comment(
        self,
        telegram_id: int,
        comment_text: str,
    ) -> None:
        await self.execute(
            """
            INSERT INTO survey_open_comments (
                telegram_id, comment_text, created_at
            )
            VALUES (?, ?, ?)
            """,
            [telegram_id, comment_text, utc_now_iso()],
        )
