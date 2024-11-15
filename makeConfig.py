token = "TOKEN"
with open("config.py", "w") as file:
    file.write(f"API_TOKEN = '{token}'")

print("Файл config.py успешно создан.")