"""
Скрипт для тестирования рекуррентных платежей
Искусственно инициирует списание по всем активным подпискам (кроме последней)
"""

import sys
import logging
from datetime import datetime, timedelta
from database import SessionLocal
import models

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def setup_test_payments():
    """
    Устанавливает next_payment_date в прошлое для всех активных подписок (кроме последней)
    чтобы инициировать немедленное списание
    """
    db = SessionLocal()
    try:
        # Получаем все активные подписки с автопродлением
        active_subscriptions = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.status == "active",
            models.SubscriptionHistory.auto_renewal == True,
            models.SubscriptionHistory.card_token != None
        ).order_by(models.SubscriptionHistory.created_at.desc()).all()
        
        if not active_subscriptions:
            logger.warning("❌ Нет активных подписок с автопродлением")
            return
        
        logger.info(f"📊 Найдено активных подписок: {len(active_subscriptions)}")
        
        # Пропускаем последнюю (самую новую) подписку
        subscriptions_to_test = active_subscriptions[1:] if len(active_subscriptions) > 1 else []
        
        if not subscriptions_to_test:
            logger.info("ℹ️ Только одна подписка найдена, пропускаем её (самая новая)")
            logger.info(f"   Subscription ID: {active_subscriptions[0].id}")
            logger.info(f"   User ID: {active_subscriptions[0].user_id}")
            logger.info(f"   Tariff ID: {active_subscriptions[0].tariff_id}")
            return
        
        logger.info(f"🎯 Будет обработано подписок: {len(subscriptions_to_test)}")
        logger.info(f"⏭️ Пропущена последняя подписка: ID {active_subscriptions[0].id}")
        
        # Устанавливаем next_payment_date в прошлое для инициации списания
        now = datetime.now()
        past_date = now - timedelta(minutes=5)  # 5 минут назад
        
        for idx, subscription in enumerate(subscriptions_to_test, 1):
            # Получаем информацию о тарифе
            tariff = db.query(models.Tariff).filter(
                models.Tariff.id == subscription.tariff_id
            ).first()
            
            original_tariff = None
            if subscription.original_tariff_id:
                original_tariff = db.query(models.Tariff).filter(
                    models.Tariff.id == subscription.original_tariff_id
                ).first()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📝 Подписка #{idx}/{len(subscriptions_to_test)}")
            logger.info(f"   Subscription ID: {subscription.id}")
            logger.info(f"   User ID: {subscription.user_id}")
            logger.info(f"   Tariff: {tariff.name if tariff else 'Unknown'} ({tariff.price if tariff else 0}₽)")
            if original_tariff:
                logger.info(f"   Original Tariff: {original_tariff.name} ({original_tariff.price}₽)")
            logger.info(f"   Created: {subscription.created_at}")
            logger.info(f"   Current next_payment_date: {subscription.next_payment_date}")
            logger.info(f"   Failed attempts: {subscription.failed_attempts or 0}")
            logger.info(f"   Downgrade attempts: {subscription.downgrade_attempts or 0}")
            
            # Устанавливаем дату в прошлое
            old_date = subscription.next_payment_date
            subscription.next_payment_date = past_date
            
            logger.info(f"   ✅ Установлена next_payment_date: {past_date}")
            logger.info(f"   (было: {old_date})")
        
        # Сохраняем изменения
        db.commit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Обновлено подписок: {len(subscriptions_to_test)}")
        logger.info(f"⏭️ Пропущено подписок: 1 (последняя)")
        logger.info(f"\n🔄 Теперь запустите scheduler или дождитесь следующей проверки (каждую минуту)")
        logger.info(f"   Scheduler автоматически обработает эти подписки")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при настройке тестовых платежей: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
    finally:
        db.close()


def check_results():
    """Проверяет результаты обработки платежей"""
    db = SessionLocal()
    try:
        logger.info(f"\n{'='*60}")
        logger.info("📊 ПРОВЕРКА РЕЗУЛЬТАТОВ")
        logger.info(f"{'='*60}\n")
        
        # Получаем все подписки
        all_subscriptions = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.card_token != None
        ).order_by(models.SubscriptionHistory.created_at.desc()).all()
        
        if not all_subscriptions:
            logger.warning("❌ Нет подписок с картами")
            return
        
        for idx, subscription in enumerate(all_subscriptions, 1):
            tariff = db.query(models.Tariff).filter(
                models.Tariff.id == subscription.tariff_id
            ).first()
            
            original_tariff = None
            if subscription.original_tariff_id:
                original_tariff = db.query(models.Tariff).filter(
                    models.Tariff.id == subscription.original_tariff_id
                ).first()
            
            logger.info(f"\n📝 Подписка #{idx}")
            logger.info(f"   ID: {subscription.id}")
            logger.info(f"   User: {subscription.user_id}")
            logger.info(f"   Status: {subscription.status}")
            logger.info(f"   Tariff: {tariff.name if tariff else 'Unknown'} ({tariff.price if tariff else 0}₽)")
            if original_tariff:
                logger.info(f"   Original Tariff: {original_tariff.name} ({original_tariff.price}₽)")
            logger.info(f"   Auto Renewal: {subscription.auto_renewal}")
            logger.info(f"   Next Payment: {subscription.next_payment_date}")
            logger.info(f"   Failed Attempts: {subscription.failed_attempts or 0}")
            logger.info(f"   Downgrade Attempts: {subscription.downgrade_attempts or 0}")
            logger.info(f"   Last Payment Attempt: {subscription.last_payment_attempt}")
            
            # Проверяем платежи
            payments = db.query(models.Payment).filter(
                models.Payment.user_id == subscription.user_id
            ).order_by(models.Payment.created_at.desc()).limit(3).all()
            
            if payments:
                logger.info(f"   💳 Последние платежи ({len(payments)}):")
                for payment in payments:
                    logger.info(f"      - Amount: {payment.amount}₽, Status: {payment.status}, Created: {payment.created_at}")
        
        logger.info(f"\n{'='*60}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке результатов: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()


def run_scheduler_once():
    """Запускает одну итерацию обработки платежей"""
    import asyncio
    from recurrent_payments_scheduler import RecurrentPaymentsScheduler
    
    logger.info(f"\n{'='*60}")
    logger.info("🔄 ЗАПУСК ОБРАБОТКИ ПЛАТЕЖЕЙ")
    logger.info(f"{'='*60}\n")
    
    try:
        scheduler = RecurrentPaymentsScheduler()
        asyncio.run(scheduler.process_pending_payments())
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ Обработка завершена")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске scheduler: {e}")
        import traceback
        logger.error(traceback.format_exc())


def reset_all():
    """Сбрасывает все подписки в исходное состояние"""
    db = SessionLocal()
    try:
        subscriptions = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.card_token != None
        ).all()
        
        now = datetime.now()
        
        for subscription in subscriptions:
            subscription.next_payment_date = now + timedelta(days=7)
            subscription.failed_attempts = 0
            subscription.downgrade_attempts = 0
            subscription.status = "active"
            subscription.auto_renewal = True
        
        db.commit()
        logger.info(f"✅ Сброшено подписок: {len(subscriptions)}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при сбросе: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ РЕКУРРЕНТНЫХ ПЛАТЕЖЕЙ")
    print("="*60 + "\n")
    
    print("Выберите действие:")
    print("1. Настроить тестовые платежи (установить next_payment_date в прошлое)")
    print("2. Запустить обработку платежей вручную")
    print("3. Проверить результаты")
    print("4. Полный цикл: настроить → обработать → проверить")
    print("5. Сбросить все подписки в исходное состояние")
    print()
    
    choice = input("Введите номер (1-5): ").strip()
    
    if choice == "1":
        setup_test_payments()
        print("\n✅ Готово! Теперь дождитесь работы scheduler или запустите действие 2")
        
    elif choice == "2":
        run_scheduler_once()
        
    elif choice == "3":
        check_results()
        
    elif choice == "4":
        print("\n📝 Шаг 1/3: Настройка тестовых платежей...")
        setup_test_payments()
        
        print("\n⏳ Ожидание 2 секунды...")
        import time
        time.sleep(2)
        
        print("\n📝 Шаг 2/3: Запуск обработки платежей...")
        run_scheduler_once()
        
        print("\n📝 Шаг 3/3: Проверка результатов...")
        check_results()
        
    elif choice == "5":
        confirm = input("⚠️ Вы уверены? Это сбросит все подписки (y/n): ").strip().lower()
        if confirm == 'y':
            reset_all()
        else:
            print("❌ Отменено")
            
    else:
        print("❌ Неверный выбор")


