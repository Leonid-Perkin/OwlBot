from telethon import events, Button
import asyncio
from telethon.tl.types import Channel, Chat
from telethon.errors import QueryIdInvalidError
from utils import mention_all_users, get_day_schedule, get_week_schedule, fetch_horoscope, is_user_admin, format_schedule
from menu import get_main_menu, get_group_selection_menu, get_horoscope_menu, zodiac_signs
from stats import record_message, get_day_stats, format_day_stats, get_day_messages, clear_chat_messages
from summary import generate_summary
from datetime import datetime, timedelta

submenu_messages = {}
custom_schedule_waiting = {}

@events.register(events.NewMessage)
async def count_message(event):
    if not event.chat_id:
        return
    sender = await event.get_sender()
    if not sender or getattr(sender, 'bot', False):
        return

    first_name = getattr(sender, 'first_name', '') or ''
    last_name = getattr(sender, 'last_name', '') or ''
    user_name = f"{first_name} {last_name}".strip()
    if not user_name:
        user_name = getattr(sender, 'username', '') or f"id{sender.id}"

    today = datetime.now().strftime("%Y-%m-%d")
    await record_message(event.chat_id, sender.id, user_name, today, text=event.text)

@events.register(events.NewMessage(pattern=r'^/(stats|daystats|top)'))
async def stats_command(event):
    chat_id = event.chat_id
    today = datetime.now().strftime("%Y-%m-%d")
    total_messages, active_users, top_users = await get_day_stats(chat_id, today)
    text = format_day_stats(total_messages, active_users, top_users, today)
    await event.reply(text, parse_mode='Markdown')

@events.register(events.NewMessage(pattern=r'^/(summary|digest|tldr)'))
async def summary_command(event):
    chat_id = event.chat_id
    today = datetime.now().strftime("%Y-%m-%d")
    messages = await get_day_messages(chat_id, today)
    if not messages or len(messages) < 3:
        await event.reply("В чате за сегодня недостаточно сообщений для составления выжимки (нужно хотя бы 3 сообщения).")
        return
    wait_msg = await event.reply("⏳ Читаю сообщения и составляю выжимку за сегодня...")
    try:
        summary_text = await generate_summary(messages, today)
        try:
            await wait_msg.edit(
                summary_text,
                parse_mode='Markdown',
                buttons=[[Button.inline("🔄 Начать с чистого листа", b"reset_summary_context")]]
            )
        except Exception:
            await wait_msg.edit(
                summary_text,
                parse_mode=None,
                buttons=[[Button.inline("🔄 Начать с чистого листа", b"reset_summary_context")]]
            )
    except Exception as e:
        await wait_msg.edit(f"❌ Ошибка при формировании выжимки: {e}")

@events.register(events.NewMessage(pattern=r'^/(resetsummary|clear_summary|clearsummary)'))
async def reset_summary_command(event):
    chat_id = event.chat_id
    today = datetime.now().strftime("%Y-%m-%d")
    await clear_chat_messages(chat_id, today)
    await event.reply("🔄 Контекст переписки для выжимки сброшен! Теперь выжимка начнётся с чистого листа.")

@events.register(events.NewMessage(pattern='/start'))
async def start_command(event):
    await event.reply("Привет! Я бот для управления группой. Выбери действие:", buttons=get_main_menu())

@events.register(events.NewMessage(pattern=r'(?i).*@all.*'))
async def mention_all_text(event):
    chat = await event.get_chat()
    if not isinstance(chat, (Channel, Chat)):
        await event.reply("Этот запрос работает только в группах.")
        return
    sender = await event.get_sender()
    chat_id = event.chat_id
    if not await is_user_admin(chat_id, sender.id, event.client):
        await event.reply("Эта команда доступна только администраторам чата.")
        return
    bot = await event.client.get_me()
    bot_id = bot.id
    await mention_all_users(event.client, chat_id, bot_id, event)

@events.register(events.NewMessage)
async def handle_custom_schedule_input(event):
    key = (event.chat_id, event.sender_id)
    if key not in custom_schedule_waiting:
        return
    text = event.text.strip()
    if text.startswith("/"):
        del custom_schedule_waiting[key]
        return
    if len(text.split()) >= 2:
        group, date = text.split(maxsplit=1)
        try:
            datetime.strptime(date, "%Y-%m-%d")
            del custom_schedule_waiting[key]
            schedule = await get_day_schedule(group, date)
            message = format_schedule(schedule, date)
            await event.reply(message, parse_mode='Markdown')
        except ValueError:
            await event.reply("Неверный формат даты. Используйте YYYY-MM-DD (например, 2025-03-15)")
    else:
        await event.reply("Неверный формат. Используйте: <группа> <дата YYYY-MM-DD>")

@events.register(events.CallbackQuery)
async def handle_callback(event):
    chat = await event.get_chat()
    bot = await event.client.get_me()
    bot_id = bot.id
    chat_id = event.chat_id
    user_id = event.sender_id

    data = event.data.decode('utf-8')

    if event.data == b"mention_all":
        if not isinstance(chat, (Channel, Chat)):
            try:
                await event.answer("Эта команда работает только в группах.", alert=True)
            except QueryIdInvalidError:
                pass
            return
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

    elif event.data == b"day_stats":
        today = datetime.now().strftime("%Y-%m-%d")
        total_messages, active_users, top_users = await get_day_stats(chat_id, today)
        message = format_day_stats(total_messages, active_users, top_users, today)
        await event.reply(message, parse_mode='Markdown')

    elif event.data == b"day_summary":
        today = datetime.now().strftime("%Y-%m-%d")
        messages = await get_day_messages(chat_id, today)
        if not messages or len(messages) < 3:
            await event.reply("В чате за сегодня недостаточно сообщений для составления выжимки (нужно хотя бы 3 сообщения).")
            return
        wait_msg = await event.reply("⏳ Читаю сообщения и составляю выжимку за сегодня...")
        try:
            summary_text = await generate_summary(messages, today)
            try:
                await wait_msg.edit(
                    summary_text,
                    parse_mode='Markdown',
                    buttons=[[Button.inline("🔄 Начать с чистого листа", b"reset_summary_context")]]
                )
            except Exception:
                await wait_msg.edit(
                    summary_text,
                    parse_mode=None,
                    buttons=[[Button.inline("🔄 Начать с чистого листа", b"reset_summary_context")]]
                )
        except Exception as e:
            await wait_msg.edit(f"❌ Ошибка при формировании выжимки: {e}")

    elif event.data == b"reset_summary_context":
        today = datetime.now().strftime("%Y-%m-%d")
        await clear_chat_messages(chat_id, today)
        try:
            await event.answer("Контекст выжимки сброшен! Новые сообщения начнут накапливаться с нуля.", alert=True)
        except QueryIdInvalidError:
            pass
        await event.reply("🔄 Контекст переписки сброшен! Теперь выжимка начнётся с чистого листа.")

    elif data.startswith("horoscope_"):
        parts = data.split("_")
        sign = parts[1]
        main_menu_msg_id = int(parts[2])
        rus_name, emoji = next(((k, v[1]) for k, v in zodiac_signs.items() if v[0] == sign), ("Неизвестный знак", "❓"))
        horoscope = await asyncio.to_thread(fetch_horoscope, sign)
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
        custom_schedule_waiting[(chat_id, user_id)] = event.message_id
        await event.reply("Введите команду в формате: <группа> <дата YYYY-MM-DD>\n"
                         "Например: БАСО-03-24 2025-03-15",
                         buttons=[[Button.inline("Отмена", b"cancel")]])

    elif event.data == b"cancel":
        key = (chat_id, user_id)
        if key in custom_schedule_waiting:
            del custom_schedule_waiting[key]
        try:
            await event.answer("Действие отменено.")
        except QueryIdInvalidError:
            pass
        await event.reply("Действие отменено.")