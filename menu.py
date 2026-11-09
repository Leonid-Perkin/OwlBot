from telethon import Button

zodiac_signs = {
    "Овен": ("aries", "♈"),
    "Телец": ("taurus", "♉"),
    "Близнецы": ("gemini", "♊"),
    "Рак": ("cancer", "♋"),
    "Лев": ("leo", "♌"),
    "Дева": ("virgo", "♍"),
    "Весы": ("libra", "♎"),
    "Скорпион": ("scorpio", "♏"),
    "Стрелец": ("sagittarius", "♐"),
    "Козерог": ("capricorn", "♑"),
    "Водолей": ("aquarius", "♒"),
    "Рыбы": ("pisces", "♓")
}

def get_main_menu():
    return [
        [Button.inline("👥 Упомянуть всех", b"mention_all")],
        [Button.inline("📅 Расписание на сегодня", b"schedule_today")],
        [Button.inline("📆 Расписание на завтра", b"schedule_tomorrow")],
        [Button.inline("🗓 Расписание на неделю", b"schedule_week")],
        [Button.inline("✏ Указать дату и группу", b"schedule_custom")],
        [Button.inline("🌟 Гороскоп на сегодня", b"horoscope")],
        [Button.inline("📊 Сообщения за день", b"day_stats")]
    ]

def get_group_selection_menu(action, main_menu_msg_id):
    return [
        [Button.inline("БАСО-01-24", f"{action}_БАСО-01-24_{main_menu_msg_id}".encode())],
        [Button.inline("БАСО-02-24", f"{action}_БАСО-02-24_{main_menu_msg_id}".encode())],
        [Button.inline("БАСО-03-24", f"{action}_БАСО-03-24_{main_menu_msg_id}".encode())],
        [Button.inline("БАСО-04-24", f"{action}_БАСО-04-24_{main_menu_msg_id}".encode())],
        [Button.inline("🔙 Назад", f"back_to_main_{main_menu_msg_id}".encode())]
    ]

def get_horoscope_menu(main_menu_msg_id):
    buttons = []
    for rus_name, (sign, emoji) in zodiac_signs.items():
        buttons.append([Button.inline(f"{emoji} {rus_name}", f"horoscope_{sign}_{main_menu_msg_id}".encode())])
    buttons.append([Button.inline("🔙 Назад", f"back_to_main_{main_menu_msg_id}".encode())])
    return buttons