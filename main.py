import asyncio
from telethon import TelegramClient
from handlers import start_command, mention_all_text, handle_callback
with open('tg.key', 'r') as f:
    config = dict(line.strip().split('=') for line in f if '=' in line)

API_ID = int(config['API_ID'])
API_HASH = config['API_HASH']
BOT_TOKEN = config['BOT_TOKEN']

client = TelegramClient('bot_session', API_ID, API_HASH)

client.add_event_handler(start_command)
client.add_event_handler(mention_all_text)
client.add_event_handler(handle_callback)

async def main():
    await client.start(bot_token=BOT_TOKEN)
    bot = await client.get_me()
    print(f"Бот запущен как @{bot.username}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())