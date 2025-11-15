"""
Тестовый скрипт для проверки рекуррентных платежей
Искусственно устанавливает дату следующего платежа в прошлое и запускает процесс списания
"""

import asyncio
import logging
from datetime import datetime, timedelta
from database import SessionLocal
import models
from recurrent_payments_scheduler import RecurrentPaymentsScheduler

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

def setup_test_payment():
    """Устанавливаем дату следующего платежа в прошлое для тестирования"""
    db = SessionLocal()
    try:
        # Находим последнюю активную подписку
        subscription = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.status == "active",
            models.SubscriptionHistory.card_token.isnot(None),
            models.SubscriptionHistory.auto_renewal == True
        ).order_by(models.SubscriptionHistory.id.desc()).first()
        
        if not subscription:
            print("❌ Не найдено активных подписок с токеном карты")
            return None
        
        print("=" * 70)
        print("📋 НАЙДЕНА ПОДПИСКА ДЛЯ ТЕСТА:")
        print("=" * 70)
        print(f"ID подписки: {subscription.id}")
        print(f"User ID: {subscription.user_id}")
        print(f"Tariff ID: {subscription.tariff_id}")
        print(f"Card Token: {subscription.card_token[:20]}...")
        print(f"Auto Renewal: {subscription.auto_renewal}")
        print(f"Текущая дата следующего платежа: {subscription.next_payment_date}")
        print(f"Дата окончания: {subscription.end_date}")
        print("=" * 70)
        
        # Устанавливаем next_payment_date в прошлое (вчера)
        test_date = datetime.now() - timedelta(days=1)
        subscription.next_payment_date = test_date
        
        db.commit()
        
        print(f"\n✅ Установлена тестовая дата платежа: {test_date}")
        print(f"   (это {(datetime.now() - test_date).total_seconds() / 3600:.1f} часов назад)")
        print("\n🔄 Теперь запускаем процесс проверки и списания...")
        print("=" * 70)
        
        return subscription.id
        
    except Exception as e:
        print(f"❌ Ошибка настройки теста: {e}")
        db.rollback()
        return None
    finally:
        db.close()

async def run_payment_check():
    """Запускаем проверку и обработку платежей"""
    print("\n🚀 ЗАПУСК ПРОЦЕССА РЕКУРРЕНТНЫХ ПЛАТЕЖЕЙ\n")
    
    try:
        # Создаем экземпляр планировщика и запускаем одну проверку
        scheduler = RecurrentPaymentsScheduler()
        await scheduler.process_pending_payments()
        print("\n✅ Процесс завершен")
    except Exception as e:
        print(f"\n❌ Ошибка при обработке платежей: {e}")
        import traceback
        traceback.print_exc()

def check_results(subscription_id):
    """Проверяем результаты после списания"""
    db = SessionLocal()
    try:
        print("\n" + "=" * 70)
        print("📊 РЕЗУЛЬТАТЫ ПОСЛЕ ОБРАБОТКИ:")
        print("=" * 70)
        
        # Проверяем подписку
        subscription = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.id == subscription_id
        ).first()
        
        if subscription:
            print(f"\n📦 ПОДПИСКА (ID: {subscription_id}):")
            print(f"   Status: {subscription.status}")
            print(f"   Next Payment Date: {subscription.next_payment_date}")
            print(f"   End Date: {subscription.end_date}")
            print(f"   Failed Attempts: {subscription.failed_attempts}")
            print(f"   Auto Renewal: {subscription.auto_renewal}")
            
            if subscription.next_payment_date:
                time_until = subscription.next_payment_date - datetime.now()
                print(f"   Время до следующего платежа: {time_until.total_seconds() / 3600:.1f} часов")
        
        # Проверяем последний платеж
        last_payment = db.query(models.Payment).filter(
            models.Payment.user_id == subscription.user_id
        ).order_by(models.Payment.id.desc()).first()
        
        if last_payment:
            print(f"\n💳 ПОСЛЕДНИЙ ПЛАТЕЖ:")
            print(f"   ID: {last_payment.id}")
            print(f"   Amount: {last_payment.amount} {last_payment.currency}")
            print(f"   Status: {last_payment.status}")
            print(f"   Transaction ID: {last_payment.transaction_id}")
            print(f"   Created At: {last_payment.created_at}")
            print(f"   Is Recurrent: {last_payment.is_recurrent}")
        
        # Проверяем пользователя
        user = db.query(models.User).filter(
            models.User.user_id == subscription.user_id
        ).first()
        
        if user:
            print(f"\n👤 ПОЛЬЗОВАТЕЛЬ:")
            print(f"   User ID: {user.user_id}")
            print(f"   Current Tariff ID: {user.current_tariff_id}")
            print(f"   Is Paid: {user.is_paid}")
            print(f"   Subscription End: {user.subscription_end}")
        
        print("\n" + "=" * 70)
        
        # Анализ результата
        print("\n🎯 АНАЛИЗ:")
        if subscription.next_payment_date and subscription.next_payment_date > datetime.now():
            print("✅ Дата следующего платежа обновлена на будущее")
        else:
            print("⚠️ Дата следующего платежа не обновлена или все еще в прошлом")
        
        if last_payment and last_payment.created_at > datetime.now() - timedelta(minutes=5):
            print("✅ Создан новый платеж в последние 5 минут")
        else:
            print("⚠️ Новый платеж не был создан")
        
        if subscription.failed_attempts == 0:
            print("✅ Нет неудачных попыток списания")
        else:
            print(f"⚠️ Неудачных попыток: {subscription.failed_attempts}")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Ошибка проверки результатов: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

async def main():
    """Главная функция теста"""
    print("\n" + "=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ РЕКУРРЕНТНЫХ ПЛАТЕЖЕЙ")
    print("=" * 70)
    print("\nЭтот скрипт:")
    print("1. Найдет активную подписку с токеном карты")
    print("2. Установит дату следующего платежа в прошлое")
    print("3. Запустит процесс автоматического списания")
    print("4. Покажет результаты\n")
    
    input("Нажмите Enter для продолжения...")
    
    # Шаг 1: Настраиваем тестовые данные
    subscription_id = setup_test_payment()
    
    if not subscription_id:
        print("\n❌ Не удалось настроить тест")
        return
    
    print("\n⏳ Ожидание 2 секунды перед запуском...")
    await asyncio.sleep(2)
    
    # Шаг 2: Запускаем процесс списания
    await run_payment_check()
    
    print("\n⏳ Ожидание 2 секунды перед проверкой результатов...")
    await asyncio.sleep(2)
    
    # Шаг 3: Проверяем результаты
    check_results(subscription_id)
    
    print("\n✅ Тест завершен!\n")

if __name__ == "__main__":
    asyncio.run(main())
