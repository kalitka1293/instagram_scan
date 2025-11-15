"""
Скрипт для тестирования списания с конкретного аккаунта
ID плательщика: 8421135142
Транзакция: 3104923398
"""

import sys
import logging
from datetime import datetime, timedelta
from database import SessionLocal
import models
from cloudpayments_client import get_cloudpayments_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Целевой аккаунт
TARGET_USER_ID = "8421135142"
TARGET_TRANSACTION_ID = "3104923398"


def find_user_subscription():
    """Находит подписку пользователя"""
    db = SessionLocal()
    try:
        # Ищем активную подписку
        subscription = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.user_id == TARGET_USER_ID,
            models.SubscriptionHistory.status.in_(["active", "paused"])
        ).first()
        
        if not subscription:
            logger.error(f"❌ Подписка не найдена для пользователя {TARGET_USER_ID}")
            return None
        
        # Получаем информацию о тарифе
        tariff = db.query(models.Tariff).filter(
            models.Tariff.id == subscription.tariff_id
        ).first()
        
        original_tariff = None
        if subscription.original_tariff_id:
            original_tariff = db.query(models.Tariff).filter(
                models.Tariff.id == subscription.original_tariff_id
            ).first()
        
        logger.info(f"📝 Найдена подписка:")
        logger.info(f"   Subscription ID: {subscription.id}")
        logger.info(f"   User ID: {subscription.user_id}")
        logger.info(f"   Status: {subscription.status}")
        logger.info(f"   Tariff: {tariff.name if tariff else 'Unknown'} ({tariff.price if tariff else 0}₽)")
        if original_tariff:
            logger.info(f"   Original Tariff: {original_tariff.name} ({original_tariff.price}₽)")
        logger.info(f"   Auto Renewal: {subscription.auto_renewal}")
        logger.info(f"   Card Token: {subscription.card_token[:20] if subscription.card_token else 'None'}...")
        logger.info(f"   Next Payment: {subscription.next_payment_date}")
        logger.info(f"   Failed Attempts: {subscription.failed_attempts or 0}")
        logger.info(f"   Downgrade Attempts: {subscription.downgrade_attempts or 0}")
        
        return subscription, tariff, original_tariff
        
    except Exception as e:
        logger.error(f"❌ Ошибка при поиске подписки: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    finally:
        db.close()


def setup_immediate_payment(subscription):
    """Устанавливает немедленное списание"""
    db = SessionLocal()
    try:
        # Устанавливаем next_payment_date в прошлое для немедленного списания
        now = datetime.now()
        past_date = now - timedelta(minutes=5)
        
        old_date = subscription.next_payment_date
        subscription.next_payment_date = past_date
        
        db.commit()
        
        logger.info(f"✅ Установлена next_payment_date: {past_date}")
        logger.info(f"   (было: {old_date})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при настройке платежа: {e}")
        db.rollback()
        return False
    finally:
        db.close()


async def run_single_payment():
    """Запускает обработку одного платежа"""
    from recurrent_payments_scheduler import RecurrentPaymentsScheduler
    
    logger.info(f"\n{'='*60}")
    logger.info("🔄 ЗАПУСК ОБРАБОТКИ ПЛАТЕЖА")
    logger.info(f"{'='*60}\n")
    
    try:
        scheduler = RecurrentPaymentsScheduler()
        
        # Получаем подписку
        db = SessionLocal()
        subscription = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.user_id == TARGET_USER_ID,
            models.SubscriptionHistory.status.in_(["active", "paused"])
        ).first()
        
        if not subscription:
            logger.error(f"❌ Подписка не найдена для пользователя {TARGET_USER_ID}")
            return
        
        # Обрабатываем платёж
        await scheduler.process_recurrent_payment(db, subscription)
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ Обработка завершена")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске обработки: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()


def check_payment_results():
    """Проверяет результаты платежа"""
    db = SessionLocal()
    try:
        logger.info(f"\n{'='*60}")
        logger.info("📊 ПРОВЕРКА РЕЗУЛЬТАТОВ")
        logger.info(f"{'='*60}\n")
        
        # Подписка
        subscription = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.user_id == TARGET_USER_ID
        ).first()
        
        if subscription:
            tariff = db.query(models.Tariff).filter(
                models.Tariff.id == subscription.tariff_id
            ).first()
            
            logger.info(f"📝 Подписка:")
            logger.info(f"   ID: {subscription.id}")
            logger.info(f"   Status: {subscription.status}")
            logger.info(f"   Tariff: {tariff.name if tariff else 'Unknown'} ({tariff.price if tariff else 0}₽)")
            logger.info(f"   Auto Renewal: {subscription.auto_renewal}")
            logger.info(f"   Next Payment: {subscription.next_payment_date}")
            logger.info(f"   Failed Attempts: {subscription.failed_attempts or 0}")
            logger.info(f"   Downgrade Attempts: {subscription.downgrade_attempts or 0}")
            logger.info(f"   Last Payment Attempt: {subscription.last_payment_attempt}")
        
        # Платежи
        payments = db.query(models.Payment).filter(
            models.Payment.user_id == TARGET_USER_ID
        ).order_by(models.Payment.created_at.desc()).limit(5).all()
        
        if payments:
            logger.info(f"\n💳 Последние платежи ({len(payments)}):")
            for i, payment in enumerate(payments, 1):
                logger.info(f"   #{i}. Amount: {payment.amount}₽")
                logger.info(f"      Status: {payment.status}")
                logger.info(f"      Transaction ID: {payment.transaction_id}")
                logger.info(f"      Created: {payment.created_at}")
                logger.info(f"      Card Token: {payment.card_token[:20] if payment.card_token else 'None'}...")
                logger.info("")
        else:
            logger.warning("❌ Платежи не найдены")
        
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке результатов: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()


def test_cloudpayments_charge():
    """Тестирует прямое списание через CloudPayments"""
    db = SessionLocal()
    try:
        subscription = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.user_id == TARGET_USER_ID
        ).first()
        
        if not subscription or not subscription.card_token:
            logger.error("❌ Подписка или токен карты не найдены")
            return
        
        tariff = db.query(models.Tariff).filter(
            models.Tariff.id == subscription.tariff_id
        ).first()
        
        if not tariff:
            logger.error("❌ Тариф не найден")
            return
        
        logger.info(f"💳 Тестирование списания {tariff.price}₽")
        logger.info(f"   Card Token: {subscription.card_token[:20]}...")
        logger.info(f"   Tariff: {tariff.name}")
        
        # Создаём клиент CloudPayments
        cp_client = get_cloudpayments_client(test_mode=False)
        
        # Пытаемся списать
        result = cp_client.charge_token(
            amount=tariff.price,
            currency="RUB",
            card_token=subscription.card_token,
            description=f"Recurrent payment for {tariff.name}",
            transaction_id=f"test_{TARGET_TRANSACTION_ID}_{int(datetime.now().timestamp())}"
        )
        
        logger.info(f"📊 Результат CloudPayments:")
        logger.info(f"   Success: {result.get('Success')}")
        logger.info(f"   Message: {result.get('Message')}")
        logger.info(f"   Transaction ID: {result.get('Model', {}).get('TransactionId')}")
        
        if result.get('Success'):
            logger.info("✅ Списание успешно!")
        else:
            logger.error("❌ Списание не удалось")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании CloudPayments: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print(f"🧪 ТЕСТИРОВАНИЕ СПИСАНИЯ ДЛЯ ПОЛЬЗОВАТЕЛЯ {TARGET_USER_ID}")
    print("="*60 + "\n")
    
    print("Выберите действие:")
    print("1. Найти подписку пользователя")
    print("2. Настроить немедленное списание")
    print("3. Запустить обработку платежа")
    print("4. Проверить результаты")
    print("5. Тестировать CloudPayments напрямую")
    print("6. Полный цикл: найти → настроить → обработать → проверить")
    print()
    
    choice = input("Введите номер (1-6): ").strip()
    
    if choice == "1":
        find_user_subscription()
        
    elif choice == "2":
        result = find_user_subscription()
        if result:
            subscription, tariff, original_tariff = result
            setup_immediate_payment(subscription)
        
    elif choice == "3":
        import asyncio
        asyncio.run(run_single_payment())
        
    elif choice == "4":
        check_payment_results()
        
    elif choice == "5":
        test_cloudpayments_charge()
        
    elif choice == "6":
        print("\n📝 Шаг 1/4: Поиск подписки...")
        result = find_user_subscription()
        if not result:
            print("❌ Подписка не найдена, завершение")
            exit(1)
        
        subscription, tariff, original_tariff = result
        
        print("\n📝 Шаг 2/4: Настройка немедленного списания...")
        if not setup_immediate_payment(subscription):
            print("❌ Ошибка настройки, завершение")
            exit(1)
        
        print("\n⏳ Ожидание 2 секунды...")
        import time
        time.sleep(2)
        
        print("\n📝 Шаг 3/4: Запуск обработки платежа...")
        import asyncio
        asyncio.run(run_single_payment())
        
        print("\n📝 Шаг 4/4: Проверка результатов...")
        check_payment_results()
        
    else:
        print("❌ Неверный выбор")
