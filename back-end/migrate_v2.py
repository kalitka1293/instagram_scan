"""
Миграция базы данных для новой асинхронной системы парсинга
"""

from sqlalchemy import create_engine, text
from config import DATABASE_URL

def migrate_database():
    """Добавляет новые поля для асинхронного парсинга"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            print("🔄 Начинаем миграцию базы данных...")
            
            # Добавляем новые поля в таблицу instagram_profiles
            migration_queries = [
                "ALTER TABLE instagram_profiles ADD COLUMN parsing_status VARCHAR(20) DEFAULT 'completed'",
                "ALTER TABLE instagram_profiles ADD COLUMN parse_task_id VARCHAR(100)",
                "ALTER TABLE instagram_profiles ADD COLUMN followers_parsed_at DATETIME",
                "ALTER TABLE instagram_profiles ADD COLUMN followings_parsed_at DATETIME"
            ]
            
            for query in migration_queries:
                try:
                    connection.execute(text(query))
                    print(f"✅ Выполнено: {query}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"⚠️  Поле уже существует: {query}")
                    else:
                        print(f"❌ Ошибка: {query} - {e}")
            
            connection.commit()
            print("✅ Миграция завершена успешно!")
            
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")

if __name__ == "__main__":
    migrate_database()









