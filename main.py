import asyncio
import os
import sys
from telethon import TelegramClient
from handlers import (
    start_command,
    mention_all_text,
    handle_callback,
    handle_custom_schedule_input,
    count_message,
    stats_command,
    summary_command,
    reset_summary_command
)
from stats import init_stats_db

init_stats_db()

def load_config(filepath='tg.key'):
    if not os.path.exists(filepath):
        print(f"Ошибка: Файл конфигурации '{filepath}' не найден!")
        print("Создайте его вручную или запустите: python makeTGkey.py")
        sys.exit(1)

    config = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
            elif ':' in line:
                key, val = line.split(':', 1)
            else:
                continue
            config[key.strip().upper()] = val.strip().strip('"\'')

    required = ['API_ID', 'API_HASH', 'BOT_TOKEN']
    missing = [k for k in required if k not in config]
    if missing:
        print(f"Ошибка в файле '{filepath}': отсутствуют обязательные ключи: {', '.join(missing)}")
        sys.exit(1)

    return config

config = load_config()

API_ID = int(config['API_ID'])
API_HASH = config['API_HASH']
BOT_TOKEN = config['BOT_TOKEN']

client = TelegramClient('bot_session', API_ID, API_HASH)

client.add_event_handler(count_message)
client.add_event_handler(stats_command)
client.add_event_handler(summary_command)
client.add_event_handler(reset_summary_command)
client.add_event_handler(start_command)
client.add_event_handler(mention_all_text)
client.add_event_handler(handle_custom_schedule_input)
client.add_event_handler(handle_callback)

async def main():
    await client.start(bot_token=BOT_TOKEN)
    bot = await client.get_me()
    print(f"Бот запущен как @{bot.username}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
