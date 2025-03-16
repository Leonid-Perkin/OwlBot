from telethon import events, Button
import asyncio
from telethon.tl.types import Channel
from telethon.errors import QueryIdInvalidError
from utils import mention_all_users, get_day_schedule, get_week_schedule, fetch_horoscope, is_user_admin, format_schedule
from menu import get_main_menu, get_group_selection_menu, get_horoscope_menu, zodiac_signs
from datetime import datetime, timedelta

submenu_messages = {}

@events.register(events.NewMessage(pattern='/start'))
async def start_command(event):
    await event.reply("Привет! Я бот для управления группой. Выбери действие:", buttons=get_main_menu())

@events.register(events.NewMessage(pattern=r'(?i).*@all.*'))
async def mention_all_text(event):
    chat = await event.get_chat()
    if not isinstance(chat, Channel):
        await event.reply("Этот запрос работает только в группах.")
        return
    sender = await event.get_sender()
    chat_id = chat.id
    if not await is_user_admin(chat_id, sender.id, event.client):
        await event.reply("Эта команда доступна только администраторам чата.")
        return
    bot = await event.client.get_me()
    bot_id = bot.id
    await mention_all_users(event.client, chat_id, bot_id, event)

@events.register(events.CallbackQuery)
async def handle_callback(event):
    chat = await event.get_chat()
    if not isinstance(chat, Channel):
        try:
            await event.answer("Эта команда работает только в группах.", alert=True)
        except QueryIdInvalidError:
            pass
        return

    bot = await event.client.get_me()
    bot_id = bot.id
    chat_id = chat.id
    user_id = event.sender_id

    data = event.data.decode('utf-8')

    if event.data == b"mention_all":
        if not await is_user_admin(chat_id, user_id, event.client):
            try:
                await event.answer("Эта функция доступна только администраторам чата.", alert=True)
            except QueryIdInvalidError:
                pass
            return
        await mention_all_users(event.client, chat_id, bot_id, event)

    elif event.data == b"schedule_today":
        main_menu_msg_id = event.message_id
        msg = await event.reply("Выберите группу для расписания на сегодня:", 
                              buttons=get_group_selection_menu("schedule_today", main_menu_msg_id))
        submenu_messages[(chat_id, main_menu_msg_id)] = msg.id

    elif event.data == b"schedule_tomorrow":
        main_menu_msg_id = event.message_id
        msg = await event.reply("Выберите группу для расписания на завтра:", 
                              buttons=get_group_selection_menu("schedule_tomorrow", main_menu_msg_id))
        submenu_messages[(chat_id, main_menu_msg_id)] = msg.id

    elif event.data == b"schedule_week":
        main_menu_msg_id = event.message_id
        msg = await event.reply("Выберите группу для расписания на неделю:", 
                              buttons=get_group_selection_menu("schedule_week", main_menu_msg_id))
        submenu_messages[(chat_id, main_menu_msg_id)] = msg.id

    elif data.startswith("schedule_today_"):
        parts = data.split("_")
        group = parts[2]
        main_menu_msg_id = int(parts[3])
        today = datetime.now().strftime("%Y-%m-%d")
        schedule = await get_day_schedule(group, today)
        message = format_schedule(schedule, today)
        await event.reply(message, parse_mode='Markdown')
        parent_key = (chat_id, main_menu_msg_id)
        if parent_key in submenu_messages:
            await event.client.delete_messages(chat_id, submenu_messages[parent_key])
            del submenu_messages[parent_key]

    elif data.startswith("schedule_tomorrow_"):
        parts = data.split("_")
        group = parts[2]
        main_menu_msg_id = int(parts[3])
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        schedule = await get_day_schedule(group, tomorrow)
        message = format_schedule(schedule, tomorrow)
        await event.reply(message, parse_mode='Markdown')
        parent_key = (chat_id, main_menu_msg_id)
        if parent_key in submenu_messages:
            await event.client.delete_messages(chat_id, submenu_messages[parent_key])
            del submenu_messages[parent_key]

    elif data.startswith("schedule_week_"):
        parts = data.split("_")
        group = parts[2]
        main_menu_msg_id = int(parts[3])
        await event.reply("⏳ Загружаю расписание на неделю, пожалуйста, подождите...")
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        start_date = start_of_week.strftime("%Y-%m-%d")
        week_schedule = await get_week_schedule(group, start_date)
        for date, schedule in week_schedule.items():
            message = format_schedule(schedule, date)
            await event.reply(message, parse_mode='Markdown')
            await asyncio.sleep(0.5)
        parent_key = (chat_id, main_menu_msg_id)
        if parent_key in submenu_messages:
            await event.client.delete_messages(chat_id, submenu_messages[parent_key])
            del submenu_messages[parent_key]

    elif event.data == b"horoscope":
        main_menu_msg_id = event.message_id
        msg = await event.reply("Выберите знак зодиака для гороскопа на сегодня:", 
                              buttons=get_horoscope_menu(main_menu_msg_id))
        submenu_messages[(chat_id, main_menu_msg_id)] = msg.id

    elif data.startswith("horoscope_"):
        parts = data.split("_")
        sign = parts[1]
        main_menu_msg_id = int(parts[2])
        rus_name, emoji = next(((k, v[1]) for k, v in zodiac_signs.items() if v[0] == sign), ("Неизвестный знак", "❓"))
        horoscope = fetch_horoscope(sign)
        message = (
            f"{emoji} **Гороскоп для {rus_name} на сегодня** {emoji}\n"
            f"────────────────────\n"
            f"{horoscope}\n"
            f"────────────────────"
        )
        await event.reply(message, parse_mode='Markdown')
        parent_key = (chat_id, main_menu_msg_id)
        if parent_key in submenu_messages:
            await event.client.delete_messages(chat_id, submenu_messages[parent_key])
            del submenu_messages[parent_key]

    elif data.startswith("back_to_main_"):
        main_menu_msg_id = int(data.split("_")[-1])
        await event.reply("Выбери действие:", buttons=get_main_menu())
        parent_key = (chat_id, main_menu_msg_id)
        if parent_key in submenu_messages:
            await event.client.delete_messages(chat_id, submenu_messages[parent_key])
            del submenu_messages[parent_key]

    elif event.data == b"schedule_custom":
        await event.reply("Введите команду в формате: <группа> <дата YYYY-MM-DD>\n"
                         "Например: БАСО-03-24 2025-03-15",
                         buttons=[[Button.inline("Отмена", b"cancel")]])
        
        @event.client.on(events.NewMessage(chats=chat_id))
        async def handle_custom_schedule(event_custom):
            text = event_custom.text.strip()
            if len(text.split()) >= 2:
                group, date = text.split(maxsplit=1)
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                    schedule = await get_day_schedule(group, date)
                    message = format_schedule(schedule, date)
                    await event_custom.reply(message, parse_mode='Markdown')
                except ValueError:
                    await event_custom.reply("Неверный формат даты. Используйте YYYY-MM-DD (например, 2025-03-15)")
            else:
                await event_custom.reply("Неверный формат. Используйте: <группа> <дата YYYY-MM-DD>")
            event.client.remove_event_handler(handle_custom_schedule)

        @event.client.on(events.CallbackQuery(data=b"cancel", chats=chat_id))
        async def cancel_handler(event_cancel):
            await event_cancel.reply("Действие отменено")
            event.client.remove_event_handler(handle_custom_schedule)