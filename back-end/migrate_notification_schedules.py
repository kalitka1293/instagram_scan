#!/usr/bin/env python3
"""
Миграция для добавления колонок error_message и retry_count в notification_schedules
"""

from database import SessionLocal, engine
import models
from sqlalchemy import text

def migrate():
    """Добавить недостающие колонки"""
    db = SessionLocal()
    
    try:
        print("🔄 Проверка и добавление колонок в notification_schedules...")
        
        # Проверяем существование таблицы
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='notification_schedules'"))
        if not result.fetchone():
            print("⚠️ Таблица notification_schedules не существует, создаём все таблицы...")
            models.Base.metadata.create_all(bind=engine)
            print("✅ Таблицы созданы")
            return
        
        # Получаем список колонок
        result = db.execute(text("PRAGMA table_info(notification_schedules)"))
        columns = [row[1] for row in result.fetchall()]
        print(f"Существующие колонки: {columns}")
        
        # Проверяем наличие error_message
        if 'error_message' not in columns:
            print("➕ Добавляем колонку error_message...")
            db.execute(text("ALTER TABLE notification_schedules ADD COLUMN error_message TEXT"))
            print("✅ Колонка error_message добавлена")
        else:
            print("✓ Колонка error_message уже существует")
        
        # Проверяем наличие retry_count
        if 'retry_count' not in columns:
            print("➕ Добавляем колонку retry_count...")
            db.execute(text("ALTER TABLE notification_schedules ADD COLUMN retry_count INTEGER DEFAULT 0"))
            print("✅ Колонка retry_count добавлена")
        else:
            print("✓ Колонка retry_count уже существует")
        
        db.commit()
        print("\n✅ Миграция notification_schedules завершена успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка миграции: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()






