from urllib.parse import quote
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def get_schedule(group: str, date: str):
    encoded_group = quote(group)
    base_url = f"https://schedule-of.mirea.ru/?scheduleTitle={encoded_group}&date="
    url = f"{base_url}{date}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url)
        page.wait_for_load_state("networkidle")
        html_content = page.content()
        browser.close()
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
group = "БАСО-03-24"
date = "2024-12-19"
schedule = get_schedule(group, date)
for item in schedule:
    print(f"Время и предмет: {item['time_subject']}")
    print(f"Аудитория: {item['room']}, Преподаватель: {item['teacher']}")
    print("-" * 50)
