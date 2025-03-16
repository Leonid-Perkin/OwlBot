import asyncio
from telethon.tl.types import ChannelParticipantsAdmins
from urllib.parse import quote
from playwright.async_api import async_playwright
import json
import os
import time
import re
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from telethon.errors import QueryIdInvalidError

CACHE_DIR = "schedule_cache"
CACHE_TTL = 86400

def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

async def mention_all_users(client, chat_id, bot_id, event=None):
    participants = await client.get_participants(chat_id)
    if not participants:
        await client.send_message(chat_id, "Не удалось получить список участников.")
        return
    batch_size = 100
    for batch in chunk_list(participants, batch_size):
        mention_str = ' '.join(f'<a href="tg://user?id={p.id}">{p.first_name or "User"}</a>' 
                            for p in batch if p.id != bot_id)
        await client.send_message(chat_id, mention_str, parse_mode='html')
    if event and hasattr(event, 'answer'):
        try:
            await event.answer("Все пользователи упомянуты!", alert=True)
        except QueryIdInvalidError:
            pass
    else:
        await client.send_message(chat_id, "Все пользователи упомянуты!")

def is_cache_valid(cache_filename: str) -> bool:
    if not os.path.exists(cache_filename):
        return False
    return (time.time() - os.path.getmtime(cache_filename)) < CACHE_TTL

def load_from_cache(group: str, date: str) -> dict | None:
    cache_filename = os.path.join(CACHE_DIR, f"{group}_{date}.json")
    if is_cache_valid(cache_filename):
        with open(cache_filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_to_cache(group: str, date: str, schedule: list):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    cache_filename = os.path.join(CACHE_DIR, f"{group}_{date}.json")
    with open(cache_filename, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

async def get_day_schedule(group: str, date: str) -> list:
    cached_schedule = load_from_cache(group, date)
    if cached_schedule is not None:
        return cached_schedule
    
    encoded_group = quote(group)
    url = f"https://schedule-of.mirea.ru/?scheduleTitle={encoded_group}&date={date}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            extra_http_headers={"Accept": "text/html,application/xhtml+xml"}
        )
        page = await context.new_page()
        
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        
        schedule_blocks = await page.query_selector_all('div.TimeLine_fullcalendarText__fm4tW')
        schedule = []
        period = "Не указан"
        
        for block in schedule_blocks:
            time_subject_elem = await block.query_selector('strong.TimeLine_eventTitle__oq7tU')
            time_subject_text = await time_subject_elem.inner_text() if time_subject_elem else "Нет данных"
            time_subject_text = time_subject_text.strip()
            
            if "неделя" in time_subject_text.lower() and not any(char in time_subject_text for char in [":", "-"]):
                period = time_subject_text
                continue
            elif "сессия" in time_subject_text.lower() and not any(char in time_subject_text for char in [":", "-"]):
                period = "Сессия"
                continue
            
            if not any(char.isdigit() for char in time_subject_text):
                continue
            
            time_match = re.match(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*(.+)", time_subject_text)
            if time_match:
                start_time, end_time, subject = time_match.groups()
                time = f"{start_time} - {end_time}"
                subject = subject.strip()
            else:
                parts = time_subject_text.split(" ", 1)
                if len(parts) == 2 and "-" in parts[0]:
                    time = parts[0].replace(" ", "")
                    subject = parts[1].strip()
                else:
                    time = "Нет времени"
                    subject = time_subject_text if time_subject_text != "Нет данных" else "Нет предмета"
            
            details_block = await block.query_selector('div[style="white-space: nowrap;"]')
            room = await details_block.query_selector('strong') if details_block else None
            room = await room.inner_text() if room else "Нет данных"
            room = room.strip()
            
            await block.hover()
            await asyncio.sleep(0.1)
            dialog = await page.wait_for_selector('div[role="dialog"]', timeout=1000)
            extra_info = (await dialog.inner_text()).strip().split("\n") if dialog else []
            await page.mouse.click(0, 0)
            
            teacher = "Нет данных"
            groups = ["Нет данных о группах"]
            if extra_info:
                for line in extra_info:
                    if "Преподаватель:" in line:
                        teacher = line.replace("Преподаватель:", "").strip()
                        break
                else:
                    for line in extra_info:
                        if line.strip() and not line.startswith(("Группы:", "Аудитория:")):
                            teacher = line.strip()
                            break
                
                groups_section = False
                groups = []
                for line in extra_info:
                    if "Группы:" in line:
                        groups_section = True
                        continue
                    if groups_section and line.strip():
                        if line.startswith("БАСО-") and len(line.strip()) == 10:
                            groups.append(line.strip())
                    elif groups_section and not line.strip():
                        break
                if not groups:
                    groups = ["Нет данных о группах"]
            
            schedule.append({
                "period": period,
                "time": time,
                "subject": subject,
                "room": room,
                "teacher": teacher,
                "groups": groups
            })
        
        await browser.close()
    
    save_to_cache(group, date, schedule)
    return schedule

def calculate_break_time(end_time_prev: str, start_time_next: str) -> str:
    try:
        if " - " not in end_time_prev or " - " not in start_time_next:
            return "Не удалось рассчитать"
        end_prev = end_time_prev.split(' - ')[1]
        start_next = start_time_next.split(' - ')[0]
        end_hour, end_minute = map(int, end_prev.split(':'))
        start_hour, start_minute = map(int, start_next.split(':'))
        end_minutes = end_hour * 60 + end_minute
        start_minutes = start_hour * 60 + start_minute
        break_minutes = start_minutes - end_minutes
        if break_minutes <= 0:
            return "Нет перерыва"
        hours = break_minutes // 60
        minutes = break_minutes % 60
        if hours > 0:
            return f"{hours} ч {minutes} мин"
        return f"{minutes} мин"
    except (ValueError, IndexError):
        return "Не удалось рассчитать"

def format_schedule(schedule, date):
    if not schedule:
        return f"📅 **{date}**\nРасписание отсутствует"
    message = [f"📅 **{date}**", f"📆 **Период:** {schedule[0]['period']}"]
    for i, item in enumerate(schedule, 1):
        entry = [
            "────────────────────",
            f"🔹 **Пара №{i}**",
            f"⏰ **Время:** {item['time']}",
            f"📚 **Предмет:** {item['subject']}",
            f"🏫 **Аудитория:** {item['room']}",
            f"👨‍🏫 **Преподаватель:** {item['teacher']}",
            f"👥 **Группы:** {', '.join(item['groups'])}",
            "────────────────────"
        ]
        message.extend(entry)
        if i < len(schedule):
            break_time = calculate_break_time(item['time'], schedule[i]['time'])
            message.append(f"⏳ Перерыв: {break_time}")
            message.append("────────────────────")
    return "\n".join(message)

async def get_week_schedule(group: str, start_date: str):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    week_schedule = {}
    for i in range(7):
        date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_schedule = await get_day_schedule(group, date)
        week_schedule[date] = daily_schedule
    return week_schedule

def fetch_horoscope(sign):
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
            return "Не удалось найти гороскоп на странице."
    except requests.exceptions.RequestException as e:
        return f"Ошибка при запросе: {e}"
    except AttributeError:
        return "Не удалось найти гороскоп на странице."

async def is_user_admin(chat_id, user_id, client):
    admins = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
    return any(admin.id == user_id for admin in admins)