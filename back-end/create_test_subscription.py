#!/usr/bin/env python3
"""
Скрипт для создания тестовой подписки пользователю
"""

import sys
from database import SessionLocal
import crud
import schemas
from datetime import datetime, timedelta

def create_test_subscription(user_id: str, tariff_name: str = "Демо"):
    """Создать тестовую подписку для пользователя"""
    db = SessionLocal()
    
    try:
        # Проверяем существование пользователя
        user = crud.get_user_by_id(db, user_id)
        if not user:
            print(f"❌ Пользователь {user_id} не найден")
            # Создаем пользователя
            user_create = schemas.UserCreate(user_id=user_id)
            user = crud.create_user(db, user_create)
            print(f"✅ Создан пользователь: {user_id}")
        
        # Ищем тариф
        tariff = crud.get_tariff_by_name(db, tariff_name)
        if not tariff:
            print(f"❌ Тариф '{tariff_name}' не найден")
            # Показываем доступные тарифы
            tariffs = crud.get_all_tariffs(db, active_only=False)
            print("Доступные тарифы:")
            for t in tariffs:
                print(f"  - {t.name} ({t.price}₽)")
            return False
        
        # Обновляем пользователя
        success = crud.update_user_tariff(db, user_id, tariff.id)
        if not success:
            print(f"❌ Не удалось обновить тариф пользователя")
            return False
        
        # Создаем запись в истории подписок
        start_date = datetime.now()
        end_date = None
        if tariff.duration_days:
            end_date = start_date + timedelta(days=tariff.duration_days)
        
        subscription_create = schemas.SubscriptionHistoryCreate(
            user_id=user_id,
            tariff_id=tariff.id,
            start_date=start_date,
            end_date=end_date,
            status="active"
        )
        
        subscription = crud.create_subscription_history(db, subscription_create)
        
        print(f"✅ Создана подписка:")
        print(f"   Пользователь: {user_id}")
        print(f"   Тариф: {tariff.name} ({tariff.price}₽)")
        print(f"   Срок: {tariff.duration_days} дней" if tariff.duration_days else f"   Запросов: {tariff.requests_count}")
        print(f"   Начало: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
        if end_date:
            print(f"   Конец: {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания подписки: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    if len(sys.argv) < 2:
        print("Использование: python create_test_subscription.py <user_id> [tariff_name]")
        print("Пример: python create_test_subscription.py dev_user_123 Демо")
        return
    
    user_id = sys.argv[1]
    tariff_name = sys.argv[2] if len(sys.argv) > 2 else "Демо"
    
    create_test_subscription(user_id, tariff_name)

if __name__ == "__main__":
    main()

