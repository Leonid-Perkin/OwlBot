import sqlite3
from datetime import datetime, timedelta

def remove_inactive_chats():
    current_time = datetime.now()
    one_year_ago = current_time - timedelta(days=365)
    
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT chat_id, date FROM date")
        chats = cursor.fetchall()
        
        for chat_id, date_str in chats:
            chat_date = datetime.strptime(date_str, "%d.%m.%Y-%H:%M")
            if chat_date < one_year_ago:
                cursor.execute("DELETE FROM date WHERE chat_id = ?", (chat_id,))
                cursor.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
                print(f"Чат с chat_id {chat_id} был удален, так как не было активности более года.")
        
        conn.commit()

remove_inactive_chats()
