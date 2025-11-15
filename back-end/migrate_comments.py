#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция для добавления поля comments_data в таблицу instagram_profiles
"""

import sqlite3
import os

def migrate_comments_field():
    """Добавляет поле comments_data в таблицу instagram_profiles"""
    db_path = "instarding_bot.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем есть ли уже столбец
        cursor.execute("PRAGMA table_info(instagram_profiles)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'comments_data' in columns:
            print("✅ Столбец comments_data уже существует")
            return True
        
        # Добавляем новый столбец
        cursor.execute("ALTER TABLE instagram_profiles ADD COLUMN comments_data TEXT")
        
        conn.commit()
        conn.close()
        
        print("✅ Столбец comments_data успешно добавлен в таблицу instagram_profiles")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        return False

if __name__ == "__main__":
    migrate_comments_field()









