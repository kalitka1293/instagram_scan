#!/usr/bin/env python3
"""
Скрипт для миграции базы данных - добавляет новые поля Telegram
"""

import sqlite3
import os

def migrate_database():
    """Добавляет новые поля в таблицу users"""
    db_path = "instarding_bot.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже поля
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_fields = [
            ("first_name", "VARCHAR(100)"),
            ("last_name", "VARCHAR(100)"),
            ("telegram_username", "VARCHAR(100)")
        ]
        
        for field_name, field_type in new_fields:
            if field_name not in columns:
                print(f"➕ Добавляем поле {field_name}")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}")
            else:
                print(f"✅ Поле {field_name} уже существует")
        
        # Создаем таблицы для уведомлений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(50) NOT NULL,
                activity_type VARCHAR(50) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                extra_data JSON,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(50) NOT NULL,
                notification_type VARCHAR(50) NOT NULL,
                scheduled_time TIMESTAMP NOT NULL,
                sent BOOLEAN DEFAULT 0,
                sent_at TIMESTAMP,
                profile_username VARCHAR(100),
                message_text TEXT,
                button_text VARCHAR(100),
                button_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Создаем индексы для производительности
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activities_user_id 
            ON user_activities(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activities_timestamp 
            ON user_activities(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notification_schedules_user_id 
            ON notification_schedules(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notification_schedules_scheduled_time 
            ON notification_schedules(scheduled_time, sent)
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ Миграция завершена успешно!")
        print("📋 Добавлены поля Telegram в таблицу users")
        print("📋 Создана таблица user_activities")
        print("📋 Создана таблица notification_schedules")
        print("📋 Добавлены индексы для производительности")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        return False

if __name__ == "__main__":
    migrate_database()
