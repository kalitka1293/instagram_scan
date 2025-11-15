"""
Скрипт для отката тестовых изменений
Восстанавливает корректную дату следующего платежа
"""

from datetime import datetime, timedelta
from database import SessionLocal
import models

def reset_payment_date():
    """Восстанавливаем корректную дату следующего платежа"""
    db = SessionLocal()
    try:
        # Находим последнюю активную подписку
        subscription = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.status == "active",
            models.SubscriptionHistory.card_token.isnot(None)
        ).order_by(models.SubscriptionHistory.id.desc()).first()
        
        if not subscription:
            print("❌ Не найдено активных подписок")
            return
        
        print("=" * 70)
        print("📋 НАЙДЕНА ПОДПИСКА:")
        print("=" * 70)
        print(f"ID: {subscription.id}")
        print(f"User ID: {subscription.user_id}")
        print(f"Текущая Next Payment Date: {subscription.next_payment_date}")
        print(f"End Date: {subscription.end_date}")
        print("=" * 70)
        
        # Получаем тариф для определения периода
        tariff = db.query(models.Tariff).filter(
            models.Tariff.id == subscription.tariff_id
        ).first()
        
        if not tariff:
            print("❌ Тариф не найден")
            return
        
        # Устанавливаем next_payment_date на основе end_date
        if subscription.end_date:
            subscription.next_payment_date = subscription.end_date
            db.commit()
            
            print(f"\n✅ Восстановлена дата следующего платежа: {subscription.next_payment_date}")
            
            time_until = subscription.next_payment_date - datetime.now()
            print(f"   Время до следующего платежа: {time_until.total_seconds() / 3600:.1f} часов")
            print(f"   ({time_until.days} дней)")
        else:
            print("⚠️ End date не установлена, устанавливаем на основе тарифа")
            subscription.next_payment_date = datetime.now() + timedelta(days=tariff.duration_days)
            db.commit()
            print(f"✅ Установлена дата: {subscription.next_payment_date}")
        
        print("\n✅ Откат выполнен успешно!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("\n🔄 ОТКАТ ТЕСТОВЫХ ИЗМЕНЕНИЙ\n")
    reset_payment_date()
    print()



