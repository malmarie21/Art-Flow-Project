from __future__ import annotations

from db import Database


def _safe_round(value: float | int | None, digits: int = 2) -> float:
    return round(float(value or 0), digits)


async def _scalar(db: Database, query: str, params: list | None = None, alias: str = "value") -> float | int:
    row = await db.fetchone(query, params or [])
    return row[alias] if row and row[alias] is not None else 0


async def build_metrics(db: Database) -> dict[str, dict]:
    groups = ["test", "control"]
    result: dict[str, dict] = {}

    for group in groups:
        starts = await _scalar(
            db,
            """
            SELECT COUNT(*) AS value
            FROM events e
            JOIN users u ON u.telegram_id = e.telegram_id
            WHERE e.event_name = 'start_clicked' AND u."group" = ?
            """,
            [group],
        )
        completed = await _scalar(
            db,
            """
            SELECT COUNT(*) AS value
            FROM events e
            JOIN users u ON u.telegram_id = e.telegram_id
            WHERE e.event_name = 'flow_completed' AND u."group" = ?
            """,
            [group],
        )
        avg_survey_score = await _scalar(
            db,
            """
            SELECT AVG(CAST(sa.selected_option AS FLOAT)) AS value
            FROM survey_answers sa
            JOIN users u ON u.telegram_id = sa.telegram_id
            WHERE u."group" = ? AND sa.survey_question_number BETWEEN 1 AND 4
            """,
            [group],
        )
        avg_nps = await _scalar(
            db,
            """
            SELECT AVG(CAST(sa.selected_option AS FLOAT)) AS value
            FROM survey_answers sa
            JOIN users u ON u.telegram_id = sa.telegram_id
            WHERE u."group" = ? AND sa.survey_question_number = 5
            """,
            [group],
        )
        avg_correct = await _scalar(
            db,
            """
            SELECT AVG(u.correct_answers_count) AS value
            FROM users u
            WHERE u."group" = ? AND u.lesson_completed_at IS NOT NULL
            """,
            [group],
        )
        full_correct = await _scalar(
            db,
            """
            SELECT COUNT(*) AS value
            FROM users u
            WHERE u."group" = ? AND u.correct_answers_count = 6
            """,
            [group],
        )
        lesson_completed = await _scalar(
            db,
            """
            SELECT COUNT(*) AS value
            FROM users u
            WHERE u."group" = ? AND u.lesson_completed_at IS NOT NULL
            """,
            [group],
        )
        avg_flow_seconds = await _scalar(
            db,
            """
            SELECT AVG(
                strftime('%s', u.survey_completed_at) - strftime('%s', u.created_at)
            ) AS value
            FROM users u
            WHERE u."group" = ? AND u.survey_completed_at IS NOT NULL
            """,
            [group],
        )
        avg_lesson_seconds = await _scalar(
            db,
            """
            SELECT AVG(
                strftime('%s', u.lesson_completed_at) - strftime('%s', u.lesson_started_at)
            ) AS value
            FROM users u
            WHERE u."group" = ? AND u.lesson_completed_at IS NOT NULL AND u.lesson_started_at IS NOT NULL
            """,
            [group],
        )

        drop_off: dict[str, int] = {}
        for question_number in range(1, 7):
            answered = await _scalar(
                db,
                """
                SELECT COUNT(DISTINCT a.telegram_id) AS value
                FROM answers a
                JOIN users u ON u.telegram_id = a.telegram_id
                WHERE u."group" = ? AND a.question_number = ?
                """,
                [group, question_number],
            )
            drop_off[f"lesson_q{question_number}"] = int(starts - answered)

        result[group] = {
            "start_clicked": int(starts),
            "flow_completed": int(completed),
            "conversion_rate": _safe_round(completed / starts if starts else 0, 4),
            "avg_survey_score": _safe_round(avg_survey_score),
            "avg_nps": _safe_round(avg_nps),
            "avg_correct_answers": _safe_round(avg_correct),
            "full_correct_share": _safe_round(full_correct / lesson_completed if lesson_completed else 0, 4),
            "avg_lesson_duration_sec": _safe_round(avg_lesson_seconds),
            "avg_flow_duration_sec": _safe_round(avg_flow_seconds),
            "drop_off": drop_off,
        }

    test_cr = result["test"]["conversion_rate"]
    control_cr = result["control"]["conversion_rate"]
    uplift = ((test_cr - control_cr) / control_cr) if control_cr else 0.0
    result["summary"] = {
        "cr_uplift_test_vs_control": _safe_round(uplift, 4),
    }
    return result
