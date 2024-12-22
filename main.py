import asyncio
import sqlite3
import os
import json
import requests
from datetime import datetime
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging
from config import API_TOKEN
class DeleteChatState(StatesGroup):
    waiting_for_confirmation = State() 
class HoroscopeState(StatesGroup):
    waiting_for_choice = State()
class EmailLecturerState(StatesGroup):
    waiting_for_name = State()
logging.basicConfig(level=logging.WARN)
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
async def remove_user_from_db(user_id: int, chat_id: int):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
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
        cursor.execute("DELETE FROM date WHERE chat_id = ?", (chat_id,))
        conn.commit()
        users_deleted = cursor.rowcount
        logging.info(f"Удалено пользователей: {users_deleted}")
        
        cursor.execute("SELECT * FROM date WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        if result:
            logging.error(f"Чат с chat_id {chat_id} не был удален из таблицы date.")
        else:
            logging.info(f"Чат с chat_id {chat_id} успешно удален из таблицы date.")
async def get_schedule(group: str, date: str):
    encoded_group = quote(group)
    base_url = f"https://schedule-of.mirea.ru/?scheduleTitle={encoded_group}&date="
    url = f"{base_url}{date}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        html_content = await page.content()
        await browser.close()
    soup = BeautifulSoup(html_content, 'html.parser')
    schedule_blocks = soup.find_all('div', class_='TimeLine_fullcalendarText__fm4tW')
    schedule = []
    for block in schedule_blocks:
        time_and_subject = block.find('strong', class_='TimeLine_eventTitle__oq7tU')
        time_subject_text = time_and_subject.text.strip() if time_and_subject else "Нет данных"
        details_block = block.find('div', style='white-space: nowrap;')
        if details_block:
            details = details_block.find_all('strong')
            room = details[0].text.strip() if len(details) > 0 else "Нет данных"
            teacher = details_block.text.strip().replace(room, "").strip() if room != "Нет данных" else "Нет данных"
        else:
            room = "Нет данных"
            teacher = "Нет данных"
        schedule.append({
            "time_subject": time_subject_text,
            "room": room,
            "teacher": teacher
        })
    return schedule
async def fetch_horoscope(sign):
    url = f"https://horo.mail.ru/prediction/{sign}/today/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        horoscope_div = soup.find("div", class_="b6a5d4949c e45a4c1552")
        if horoscope_div:
            horoscope = horoscope_div.get_text(strip=True)
            return horoscope
        else:
            return "Не удалось найти гороскоп на странице. Проверьте структуру страницы."
    except requests.exceptions.RequestException as e:
        return f"Ошибка при запросе: {e}"
    except AttributeError:
        return "Не удалось найти гороскоп на странице. Проверьте селектор."
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    if message.chat.type == "private":
        await message.reply("Добавьте бота в чат с правами администратора")
    else:
        await add_user_to_db(message.from_user.id, message.from_user.username or "", message.chat.id)
        await message.answer("Привет! Ты был добавлен в список пользователей. Это бот для сбора всех участников чата.")
@dp.message(Command("mention_all"))
async def mention_all(message: types.Message):
    if message.chat.type == "private":
        await message.reply("Добавьте бота в чат с правами администратора")
    else:
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
    if message.chat.type == "private":
        await message.reply("Добавьте бота в чат с правами администратора")
    else:
        await message.answer("""
        Доступные команды:
        /start - Приветственное сообщение и добавление в базу данных.
        /mention_all - Упомянуть всех пользователей чата и обновить время последнего обращения.
        /remove_chat_users - Удалить всех пользователей из базы данных для этого чата.
        /schedule <группа> [дата] - Получить расписание на указанную дату. Если дата не указана, используется текущая.
        /last_interaction - Показать время последней активности в чате.
        /horoscope - Получить гороскоп на сегодня для выбранного знака зодиака.
        /EmailLecturer - Найти информацию о преподавателе по фамилии и имени.
        """)
@dp.message(Command("last_interaction"))
async def last_interaction(message: types.Message):
    if message.chat.type == "private":
        await message.reply("Добавьте бота в чат с правами администратора")
    else:
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
async def remove_chat(message: types.Message, state: FSMContext):
    if message.chat.type == "private":
        await message.reply("Добавьте бота в чат с правами администратора")
    else:
        if message.from_user.id not in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:
            await message.answer("Эта команда доступна только администраторам чата.")
            return
        await message.answer("Вы уверены, что хотите удалить всех пользователей и информацию о чате из базы данных? Ответьте 'да' для подтверждения или 'нет' для отмены.")
        await state.set_state(DeleteChatState.waiting_for_confirmation)

@dp.message(DeleteChatState.waiting_for_confirmation, F.text.lower().in_(['да', 'нет']))
async def confirm_deletion(message: types.Message, state: FSMContext):
    if message.chat.type == "private":
        await message.reply("Добавьте бота в чат с правами администратора")
    else:
        if message.text.lower() == "да":
            await remove_chat_users(message.chat.id)
            await message.answer("Все пользователи были удалены из базы данных этого чата, и информация о чате удалена из таблицы date.")
        else:
            await message.answer("Удаление отменено.")
        await state.clear()
@dp.message(Command("schedule"))
async def fetch_schedule(message: types.Message):
    if message.chat.type == "private":
        await message.reply("❌ Добавьте бота в чат с правами администратора")
    else:
        args = message.text.split()
        if len(args) < 2:
            await message.reply("📅 Укажите группу. Например: /schedule БАСО-03-24 [дата]")
            return
        group = args[1]
        date = args[2] if len(args) > 2 else datetime.now().strftime("%Y-%m-%d")

        try:
            schedule = await get_schedule(group, date)
            if schedule:
                response = f"📅 Расписание для группы {group} на {date}:\n\n"
                messages = []
                for item in schedule:
                    entry = (
                        f"🕒 Время и предмет: {item['time_subject']}\n"
                        f"🏫 Аудитория: {item['room']}, 👨‍🏫 Преподаватель: {item['teacher']}\n"
                        "\n"
                    )
                    response += entry
                messages.append(response)
                for part in messages:
                    await message.reply(part)
            else:
                await message.reply(f"❌ Расписание для группы {group} на {date} не найдено.")
        except Exception as e:
            logging.error(f"Ошибка при получении расписания: {e}")
            await message.reply("⚠️ Произошла ошибка при получении расписания. Попробуйте позже.")
async def chat_member_updated_handler(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        await add_user_to_db(event.new_chat_member.user.id, event.new_chat_member.user.username or "", event.chat.id)
        await bot.send_message(event.chat.id, f"Добавлен пользователь {event.new_chat_member.user.username}")
        logging.info(f"Пользователь {event.new_chat_member.user.id} добавлен в базу данных.")
    elif event.new_chat_member.status == "left":
        await remove_user_from_db(event.old_chat_member.user.id, event.chat.id)
        await bot.send_message(event.chat.id, f"Удалён пользователь {event.old_chat_member.user.username}")
        logging.info(f"Пользователь {event.old_chat_member.user.id} удален из базы данных.")
    elif event.new_chat_member.status == "kicked":
        await remove_user_from_db(event.old_chat_member.user.id, event.chat.id)
        await bot.send_message(event.chat.id, f"Удалён пользователь {event.old_chat_member.user.username}")
        logging.info(f"Пользователь {event.old_chat_member.user.id} удален из базы данных.")


@dp.message(Command("horoscope"))
async def fetch_horoscope_command(message: types.Message, state: FSMContext):
    if message.chat.type == "private":
        await message.reply("❌ Добавьте бота в чат с правами администратора.")
    else:
        zodiac_emojis = {
            "Овен": "♈",
            "Телец": "♉",
            "Близнецы": "♊",
            "Рак": "♋",
            "Лев": "♌",
            "Дева": "♍",
            "Весы": "♎",
            "Скорпион": "♏",
            "Стрелец": "♐",
            "Козерог": "♑",
            "Водолей": "♒",
            "Рыбы": "♓"
        }
        zodiac_signs = {
            "Овен": "aries",
            "Телец": "taurus",
            "Близнецы": "gemini",
            "Рак": "cancer",
            "Лев": "leo",
            "Дева": "virgo",
            "Весы": "libra",
            "Скорпион": "scorpio",
            "Стрелец": "sagittarius",
            "Козерог": "capricorn",
            "Водолей": "aquarius",
            "Рыбы": "pisces"
        }
        choices_message = "🔮 Выберите знак зодиака:\n\n"
        for i, rus_name in enumerate(zodiac_signs.keys(), start=1):
            emoji = zodiac_emojis.get(rus_name, "")
            choices_message += f"{i}. {emoji} {rus_name}\n"
        await message.answer(choices_message)
        await state.set_state(HoroscopeState.waiting_for_choice)
        await state.update_data(zodiac_signs=zodiac_signs)
@dp.message(HoroscopeState.waiting_for_choice)
async def handle_horoscope_choice(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    zodiac_signs = user_data.get("zodiac_signs")
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число, соответствующее вашему выбору.")
        return
    choice = int(message.text)
    if 1 <= choice <= len(zodiac_signs):
        sign = list(zodiac_signs.values())[choice - 1]
        rus_name = list(zodiac_signs.keys())[choice - 1]
        horoscope = await fetch_horoscope(sign)
        await message.answer(f"Гороскоп для {rus_name} на сегодня:")
        await message.answer(f"{horoscope}")
        await state.clear()
    else:
        await message.answer("Неверный выбор. Попробуйте снова.")
@dp.message(Command("EmailLecturer"))
async def fetch_lecturer_command(message: types.Message, state: FSMContext):
    if message.chat.type == "private":
        await message.reply("Добавьте бота в чат с правами администратора")
    else:
        await message.answer("Введите фамилию и имя преподавателя через пробел для поиска информации:")
        await state.set_state(EmailLecturerState.waiting_for_name)
@dp.message(EmailLecturerState.waiting_for_name)
async def handle_lecturer_choice(message: types.Message, state: FSMContext):
    input_name = message.text
    parts = input_name.split()
    if len(parts) < 2:
        await message.reply("Ошибка: необходимо ввести фамилию и имя через пробел.")
        return
    surname, firstname = parts[0], parts[1]
    try:
        with open('lecturers.json', 'r', encoding='utf-8') as json_file:
            lecturers = json.load(json_file)
    except FileNotFoundError:
        await message.reply("Ошибка: файл lecturers.json не найден.")
        await state.clear()
        return
    except json.JSONDecodeError:
        await message.reply("Ошибка: файл lecturers.json содержит некорректные данные.")
        await state.clear()
        return
    lecturer = find_lecturer_by_name(lecturers, surname, firstname)
    if lecturer:
        response = (
            f"👨‍🏫 Информация о преподавателе:\n"
            f"👨‍🏫 ФИО: {lecturer['name']}\n"
            f"📧 Email: {lecturer['email']}\n"
            f"🏛️ Кафедра: {lecturer['department']}\n"
            f"🏫 Институт: {lecturer['institute']}"
        )
        await message.reply(response)
    else:
        await message.reply("Преподаватель не найден.")
    await state.clear()
def find_lecturer_by_name(lecturers, surname, firstname):
    for lecturer in lecturers:
        if surname in lecturer['name'] and firstname in lecturer['name']:
            return lecturer
    return None
async def main():
    dp.message.register(send_welcome, Command("start"))
    dp.message.register(mention_all, Command("mention_all"))
    dp.message.register(help_message, Command("help"))
    dp.message.register(last_interaction, Command("last_interaction"))
    dp.message.register(remove_chat, Command("remove_chat_users"))
    dp.message.register(fetch_schedule, Command("schedule"))
    dp.message.register(fetch_schedule, Command("horoscope"))
    dp.message.register(fetch_schedule, Command("EmailLecturer"))
    dp.chat_member.register(chat_member_updated_handler)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
if __name__ == '__main__':
    asyncio.run(main())