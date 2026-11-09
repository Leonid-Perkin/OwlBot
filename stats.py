import sqlite3
import os
import asyncio
from datetime import datetime, timedelta

DB_PATH = os.environ.get("STATS_DB_PATH", os.path.join(os.path.dirname(__file__), "stats.db"))
DAYS_TO_KEEP = 2
_last_cleanup_date = None

def _cleanup_old_stats_sync(days_to_keep: int = DAYS_TO_KEEP):
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM message_stats WHERE date < ?", (cutoff_date,))
        cursor.execute("DELETE FROM chat_messages WHERE date < ?", (cutoff_date,))
        conn.commit()

async def cleanup_old_stats(days_to_keep: int = DAYS_TO_KEEP):
    await asyncio.to_thread(_cleanup_old_stats_sync, days_to_keep)

def init_stats_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
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
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_stats_date 
            ON message_stats(date)
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                text TEXT NOT NULL,
                date TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_date 
            ON chat_messages(chat_id, date)
        """)
        conn.commit()
    _cleanup_old_stats_sync()

def _record_message_sync(chat_id: int, user_id: int, user_name: str, date: str, text: str = None):
    global _last_cleanup_date
    if date != _last_cleanup_date:
        _cleanup_old_stats_sync()
        _last_cleanup_date = date

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO message_stats (chat_id, user_id, user_name, date, count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(chat_id, user_id, date) DO UPDATE SET
                count = count + 1,
                user_name = excluded.user_name
        """, (chat_id, user_id, user_name, date))

        if text:
            clean_text = text.strip()
            if clean_text and not clean_text.startswith('/'):
                truncated = clean_text[:500]
                ts = int(datetime.now().timestamp())
                cursor.execute("""
                    INSERT INTO chat_messages (chat_id, user_id, user_name, text, date, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (chat_id, user_id, user_name, truncated, date, ts))

        conn.commit()

async def record_message(chat_id: int, user_id: int, user_name: str, date: str = None, text: str = None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    await asyncio.to_thread(_record_message_sync, chat_id, user_id, user_name, date, text)

def _normalize_chat_ids(chat_id: int) -> list[int]:
    ids = {chat_id}
    if chat_id > 0:
        ids.add(int(f"-100{chat_id}"))
        ids.add(-chat_id)
    else:
        s = str(chat_id)
        if s.startswith("-100"):
            ids.add(int(s[4:]))
        elif s.startswith("-"):
            ids.add(int(s[1:]))
    return list(ids)

def _get_day_stats_sync(chat_id: int, date: str, limit: int = 10):
    chat_ids = _normalize_chat_ids(chat_id)
    placeholders = ",".join("?" for _ in chat_ids)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT SUM(count), COUNT(DISTINCT user_id)
            FROM message_stats
            WHERE chat_id IN ({placeholders}) AND date = ?
        """, (*chat_ids, date))
        row = cursor.fetchone()
        total_messages = row[0] or 0
        active_users = row[1] or 0

        cursor.execute(f"""
            SELECT user_name, SUM(count) as total_count
            FROM message_stats
            WHERE chat_id IN ({placeholders}) AND date = ?
            GROUP BY user_id
            ORDER BY total_count DESC
            LIMIT ?
        """, (*chat_ids, date, limit))
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

def _get_day_messages_sync(chat_id: int, date: str, limit: int = 100):
    chat_ids = _normalize_chat_ids(chat_id)
    placeholders = ",".join("?" for _ in chat_ids)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT user_name, text
            FROM chat_messages
            WHERE chat_id IN ({placeholders}) AND date = ?
            ORDER BY id ASC
            LIMIT ?
        """, (*chat_ids, date, limit))
        return cursor.fetchall()

async def get_day_messages(chat_id: int, date: str = None, limit: int = 100):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    return await asyncio.to_thread(_get_day_messages_sync, chat_id, date, limit)

def _clear_chat_messages_sync(chat_id: int, date: str = None):
    chat_ids = _normalize_chat_ids(chat_id)
    placeholders = ",".join("?" for _ in chat_ids)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if date:
            cursor.execute(f"DELETE FROM chat_messages WHERE chat_id IN ({placeholders}) AND date = ?", (*chat_ids, date))
        else:
            cursor.execute(f"DELETE FROM chat_messages WHERE chat_id IN ({placeholders})", (*chat_ids,))
        conn.commit()

async def clear_chat_messages(chat_id: int, date: str = None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    await asyncio.to_thread(_clear_chat_messages_sync, chat_id, date)
