import sqlite3
import os
import asyncio
from datetime import datetime

DB_PATH = os.environ.get("STATS_DB_PATH", os.path.join(os.path.dirname(__file__), "stats.db"))

def init_stats_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_stats (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                user_name TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (chat_id, user_id, date)
            )
        """)
        conn.commit()

def _record_message_sync(chat_id: int, user_id: int, user_name: str, date: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO message_stats (chat_id, user_id, user_name, date, count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(chat_id, user_id, date) DO UPDATE SET
                count = count + 1,
                user_name = excluded.user_name
        """, (chat_id, user_id, user_name, date))
        conn.commit()

async def record_message(chat_id: int, user_id: int, user_name: str, date: str = None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    await asyncio.to_thread(_record_message_sync, chat_id, user_id, user_name, date)

def _get_day_stats_sync(chat_id: int, date: str, limit: int = 10):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(count), COUNT(user_id)
            FROM message_stats
            WHERE chat_id = ? AND date = ?
        """, (chat_id, date))
        row = cursor.fetchone()
        total_messages = row[0] or 0
        active_users = row[1] or 0

        cursor.execute("""
            SELECT user_name, count
            FROM message_stats
            WHERE chat_id = ? AND date = ?
            ORDER BY count DESC
            LIMIT ?
        """, (chat_id, date, limit))
        top_users = cursor.fetchall()

        return total_messages, active_users, top_users

async def get_day_stats(chat_id: int, date: str = None, limit: int = 10):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    return await asyncio.to_thread(_get_day_stats_sync, chat_id, date, limit)

def format_day_stats(total_messages: int, active_users: int, top_users: list, date: str) -> str:
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        parsed_date = date

    if total_messages == 0:
        return f"📊 **Статистика за {parsed_date}**\n\nСообщений за сегодня в этом чате пока нет."

    medals = ["🥇", "🥈", "🥉"]
    lines = [
        f"📊 **Статистика сообщений за {parsed_date}**",
        "────────────────────",
        f"💬 **Всего сообщений:** {total_messages}",
        f"👥 **Активных участников:** {active_users}",
        "────────────────────",
        "🏆 **Топ участников:**"
    ]

    for idx, (name, count) in enumerate(top_users, 1):
        badge = medals[idx - 1] if idx <= 3 else f"{idx}."
        lines.append(f"{badge} **{name}** — {count} сообщ.")

    lines.append("────────────────────")
    return "\n".join(lines)
