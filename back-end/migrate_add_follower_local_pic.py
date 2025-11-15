"""
Миграция для добавления поля profile_pic_url_local в таблицу instagram_followers
"""

import sqlite3
import os

def migrate():
    db_path = "instarding_bot.db"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли уже колонка
        cursor.execute("PRAGMA table_info(instagram_followers)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'profile_pic_url_local' in columns:
            print("✅ Колонка profile_pic_url_local уже существует")
            return
        
        # Добавляем колонку
        print("📝 Добавление колонки profile_pic_url_local...")
        cursor.execute("""
            ALTER TABLE instagram_followers 
            ADD COLUMN profile_pic_url_local VARCHAR(500)
        """)
        
        conn.commit()
        print("✅ Миграция успешно выполнена!")
        print("   Добавлена колонка: profile_pic_url_local")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔄 Запуск миграции для добавления profile_pic_url_local...")
    migrate()




