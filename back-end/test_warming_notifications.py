#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы прогревающих уведомлений
"""

import asyncio
from datetime import datetime
from database import SessionLocal
import models

async def test_notifications():
    """Тест системы уведомлений"""
    print("🧪 Тестирование системы прогревающих уведомлений\n")
    
    db = SessionLocal()
    
    try:
        # 1. Проверяем наличие таблиц
        print("1️⃣ Проверка таблиц базы данных...")
        notification_count = db.query(models.NotificationSchedule).count()
        activity_count = db.query(models.UserActivity).count()
        print(f"   ✅ Таблица NotificationSchedule: {notification_count} записей")
        print(f"   ✅ Таблица UserActivity: {activity_count} записей\n")
        
        # 2. Показываем запланированные уведомления
        print("2️⃣ Запланированные уведомления:")
        notifications = db.query(models.NotificationSchedule).filter(
            models.NotificationSchedule.sent == False
        ).order_by(models.NotificationSchedule.scheduled_time).all()
        
        if notifications:
            for n in notifications[:10]:  # Показываем первые 10
                time_diff = n.scheduled_time - datetime.now()
                hours = int(time_diff.total_seconds() / 3600)
                minutes = int((time_diff.total_seconds() % 3600) / 60)
                
                print(f"   📅 {n.notification_type:10} | {n.profile_username:15} | через {hours}ч {minutes}м")
                print(f"      💬 {n.message_text}")
                print(f"      🔘 Кнопка: {n.button_text}\n")
        else:
            print("   ℹ️  Нет запланированных уведомлений\n")
        
        # 3. Показываем отправленные уведомления
        print("3️⃣ Отправленные уведомления (последние 10):")
        sent_notifications = db.query(models.NotificationSchedule).filter(
            models.NotificationSchedule.sent == True
        ).order_by(models.NotificationSchedule.sent_at.desc()).limit(10).all()
        
        if sent_notifications:
            for n in sent_notifications:
                print(f"   ✅ {n.notification_type:10} | {n.profile_username:15} | {n.sent_at}")
                print(f"      💬 {n.message_text}\n")
        else:
            print("   ℹ️  Нет отправленных уведомлений\n")
        
        # 4. Показываем активность пользователей
        print("4️⃣ Активность пользователей (последние 10):")
        activities = db.query(models.UserActivity).order_by(
            models.UserActivity.timestamp.desc()
        ).limit(10).all()
        
        if activities:
            for a in activities:
                extra = a.extra_data.get('username', '') if a.extra_data else ''
                print(f"   📊 {a.activity_type:15} | User: {a.user_id} | {extra} | {a.timestamp}")
        else:
            print("   ℹ️  Нет записей об активности\n")
        
        # 5. Статистика по типам уведомлений
        print("\n5️⃣ Статистика по типам уведомлений:")
        types = ['like', 'follower', 'message', 'observer', 'activity']
        for ntype in types:
            scheduled = db.query(models.NotificationSchedule).filter(
                models.NotificationSchedule.notification_type == ntype,
                models.NotificationSchedule.sent == False
            ).count()
            sent = db.query(models.NotificationSchedule).filter(
                models.NotificationSchedule.notification_type == ntype,
                models.NotificationSchedule.sent == True
            ).count()
            print(f"   {ntype:10} | Запланировано: {scheduled:3} | Отправлено: {sent:3}")
        
        # 6. Проверка ошибок
        print("\n6️⃣ Уведомления с ошибками:")
        failed = db.query(models.NotificationSchedule).filter(
            models.NotificationSchedule.retry_count >= 3
        ).all()
        
        if failed:
            for n in failed:
                print(f"   ❌ {n.notification_type:10} | User: {n.user_id} | Ошибка: {n.error_message}")
        else:
            print("   ✅ Нет ошибок при отправке")
        
        print("\n" + "="*70)
        print("✅ Тестирование завершено!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
    finally:
        db.close()

async def create_test_notification(user_id: str = "123456789", username: str = "testuser"):
    """Создать тестовое уведомление для немедленной отправки"""
    from notification_scheduler import register_profile_parse
    
    print(f"\n🧪 Создание тестовых уведомлений для пользователя {user_id}...")
    
    try:
        await register_profile_parse(user_id, username)
        print(f"✅ Запланировано 5 прогревающих уведомлений для @{username}")
        print(f"   - Лайк: через 5-10 минут")
        print(f"   - Наблюдатель на {username}: через 24 часа")
        print(f"   - Сообщение: через 48 часов")
        print(f"   - Наблюдатель на вашей странице: через 72 часа")
        print(f"   - Повышенная активность: через 96 часов")
        
    except Exception as e:
        print(f"❌ Ошибка создания уведомлений: {e}")

def main():
    """Главная функция"""
    print("\n" + "="*70)
    print("  ТЕСТ СИСТЕМЫ ПРОГРЕВАЮЩИХ УВЕДОМЛЕНИЙ")
    print("="*70 + "\n")
    
    asyncio.run(test_notifications())
    
    # Раскомментируйте для создания тестовых уведомлений
    # asyncio.run(create_test_notification(user_id="YOUR_TELEGRAM_ID", username="instagram"))

if __name__ == "__main__":
    main()






