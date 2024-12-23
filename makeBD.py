db_path = "users.db"
import sqlite3
import os

def check_and_update_db():
   """
   Проверяет наличие базы данных и создает ее, если она не существует.
   Создает таблицы 'users' и 'date', если они еще не созданы.
   """
   if not os.path.exists(db_path):
       with sqlite3.connect(db_path) as conn:
           cursor = conn.cursor()
           cursor.execute('''CREATE TABLE IF NOT EXISTS users
                           (user_id INTEGER, username TEXT, chat_id INTEGER, 
                            PRIMARY KEY (user_id, chat_id))''')
           cursor.execute('''CREATE TABLE IF NOT EXISTS date
                           (chat_id INTEGER PRIMARY KEY, date TEXT)''')
           conn.commit()

check_and_update_db()