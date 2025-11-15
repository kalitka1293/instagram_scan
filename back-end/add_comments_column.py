import sqlite3

def add_comments_column():
    """Добавляет столбец comments_data в таблицу instagram_profiles"""
    try:
        conn = sqlite3.connect('instarding_bot.db')
        cursor = conn.cursor()
        
        # Проверяем есть ли уже столбец
        cursor.execute("PRAGMA table_info(instagram_profiles)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'comments_data' not in columns:
            cursor.execute("ALTER TABLE instagram_profiles ADD COLUMN comments_data TEXT")
            conn.commit()
            print("✅ Столбец comments_data добавлен успешно")
        else:
            print("⚠️ Столбец comments_data уже существует")
            
    except Exception as e:
        print(f"❌ Ошибка при добавлении столбца: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_comments_column()









