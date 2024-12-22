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