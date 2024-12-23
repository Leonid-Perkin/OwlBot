from bs4 import BeautifulSoup
import json
with open('Связь с преподавателем.htm', 'r', encoding='utf-8') as file:
    html_content = file.read()
soup = BeautifulSoup(html_content, 'html.parser')
table = soup.find('table', class_='table table-striped')
lecturers = []
for row in table.find_all('tr'):
    cells = row.find_all('td')
    if len(cells) == 4:
        name = cells[0].get_text(strip=True)
        email = cells[1].find('a').get('href').replace('mailto:', '')
        department = cells[2].get_text(strip=True)
        institute = cells[3].get_text(strip=True)
        
        lecturers.append({
            'name': name,
            'email': email,
            'department': department,
            'institute': institute
        })
with open('lecturers.json', 'w', encoding='utf-8') as json_file:
    json.dump(lecturers, json_file, ensure_ascii=False, indent=4)
print("Данные успешно сохранены в lecturers.json")
def find_lecturer_by_name(lecturers, surname, firstname):
    for lecturer in lecturers:
        if surname in lecturer['name'] and firstname in lecturer['name']:
            return lecturer
    return None
input_name = input("Введите фамилию и имя преподавателя через пробел: ")
parts = input_name.split()
if len(parts) < 2:
    print("Ошибка: необходимо ввести фамилию и имя через пробел.")
else:
    surname, firstname = parts[0], parts[1]
    with open('lecturers.json', 'r', encoding='utf-8') as json_file:
        lecturers = json.load(json_file)
    lecturer = find_lecturer_by_name(lecturers, surname, firstname)
    if lecturer:
        print("\nИнформация о преподавателе:\n")
        print(f"ФИО: {lecturer['name']}")
        print(f"Email: {lecturer['email']}")
        print(f"Кафедра: {lecturer['department']}")
        print(f"Институт: {lecturer['institute']}")
    else:
        print("Преподаватель не найден.")