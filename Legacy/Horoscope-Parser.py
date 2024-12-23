import requests
from bs4 import BeautifulSoup
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
            return "Не удалось найти гороскоп на странице. Проверьте структуру страницы."
    except requests.exceptions.RequestException as e:
        return f"Ошибка при запросе: {e}"
    except AttributeError:
        return "Не удалось найти гороскоп на странице. Проверьте селектор."
if __name__ == "__main__":
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
    print("Выберите знак зодиака:")
    for i, (rus_name, _) in enumerate(zodiac_signs.items(), start=1):
        print(f"{i}. {rus_name}")
    choice = int(input("Введите номер знака: "))
    if 1 <= choice <= 12:
        sign = list(zodiac_signs.values())[choice - 1]
        rus_name = list(zodiac_signs.keys())[choice - 1]
        horoscope = fetch_horoscope(sign)
        print(f"Гороскоп для {rus_name} на сегодня:")
        print(horoscope)
    else:
        print("Неверный выбор. Попробуйте снова.")