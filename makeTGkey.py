def create_tg_key():
    print("Создание файла tg.key с Telegram API ключами")
    api_id = input("Введите API_ID: ").strip()
    api_hash = input("Введите API_HASH: ").strip()
    bot_token = input("Введите BOT_TOKEN: ").strip()

    with open('tg.key', 'w') as f:
        f.write(f"API_ID={api_id}\n")
        f.write(f"API_HASH={api_hash}\n")
        f.write(f"BOT_TOKEN={bot_token}\n")
    
    print("Файл tg.key успешно создан!")

if __name__ == '__main__':
    create_tg_key()