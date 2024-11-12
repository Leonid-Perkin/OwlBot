import asyncio
import sqlite3
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import logging
from config import API_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

db_path = "users.db"  

def check_and_update_db():
    if not os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users
                            (user_id INTEGER, username TEXT, chat_id INTEGER, 
                             PRIMARY KEY (user_id, chat_id))''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS date
                            (chat_id INTEGER PRIMARY KEY, date TEXT)''')
            conn.commit()

check_and_update_db()

def get_current_time():
    return datetime.now().strftime("%d.%m.%Y-%H:%M")

async def add_user_to_db(user_id: int, username: str, chat_id: int):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, chat_id) VALUES (?, ?, ?)", 
                       (user_id, username, chat_id))
        conn.commit()

async def update_chat_last_interaction(chat_id: int):
    current_time = get_current_time() 
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO date (chat_id, date) VALUES (?, ?)", 
                       (chat_id, current_time))
        conn.commit()

async def remove_chat_users(chat_id: int):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
        conn.commit()

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await add_user_to_db(message.from_user.id, message.from_user.username or "", message.chat.id)
    await message.answer("Привет! Ты был добавлен в список пользователей. Это бот для сбора всех участников чата.")

@dp.message(Command("mention_all"))
async def mention_all(message: types.Message):
    chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ["administrator", "creator"]:
        await message.answer("Эта команда доступна только администраторам.")
        return
    
    await update_chat_last_interaction(message.chat.id)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username FROM users WHERE chat_id = ?", (message.chat.id,))
        users = cursor.fetchall()
    
    mentions = []
    for user_id, username in users:
        mention = f"[{username}](tg://user?id={user_id})" if username else f"[User {user_id}](tg://user?id={user_id})"
        mentions.append(mention)
    
    if mentions:
        await message.answer(" ".join(mentions), parse_mode="Markdown")
    else:
        await message.answer("Нет пользователей для упоминания.")

@dp.message(Command("help"))
async def help_message(message: types.Message):
    await message.answer("""
    Доступные команды:
    /start - Приветственное сообщение и добавление в базу данных.
    /mention_all - Упомянуть всех пользователей чата и обновить время последнего обращения.
    /remove_chat_users - Удалить всех пользователей из базы данных для этого чата.
    """)
@dp.message(Command("last_interaction"))
async def last_interaction(message: types.Message):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT date FROM date WHERE chat_id = ?", (message.chat.id,))
        result = cursor.fetchone()
        if result:
            last_time = result[0] 
            await message.answer(f"Последняя активность в чате: {last_time}")
        else:
            await message.answer("Информация о последней активности отсутствует.")

@dp.message(Command("remove_chat_users"))
async def remove_chat(message: types.Message):
    if message.from_user.id not in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:
        await message.answer("Эта команда доступна только администраторам чата.")
        return
    
    await remove_chat_users(message.chat.id)
    await message.answer("Все пользователи были удалены из базы данных этого чата.")

async def main():
    dp.message.register(send_welcome, Command("start"))
    dp.message.register(mention_all, Command("mention_all"))
    dp.message.register(help_message, Command("help"))
    dp.message.register(last_interaction, Command("last_interaction"))
    dp.message.register(remove_chat, Command("remove_chat_users"))
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
