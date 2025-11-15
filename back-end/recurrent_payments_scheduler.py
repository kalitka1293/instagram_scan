"""
Планировщик рекуррентных платежей для InstardingBot
Проверяет подписки и автоматически списывает деньги по токену
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from cloudpayments_client import get_cloudpayments_client

logger = logging.getLogger(__name__)

class RecurrentPaymentsScheduler:
    """Планировщик для автоматических рекуррентных платежей"""
    
    def __init__(self):
        self.running = False
        self.check_interval = 60  # Проверка каждую минуту
        
    async def start(self):
        """Запуск планировщика"""
        self.running = True
        logger.info("🔄 Recurrent payments scheduler started")
        
        while self.running:
            try:
                await self.process_pending_payments()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in recurrent payments scheduler: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Остановка планировщика"""
        self.running = False
        logger.info("🛑 Recurrent payments scheduler stopped")
    
    async def process_pending_payments(self):
        """Обработка платежей, которые должны быть списаны"""
        db = SessionLocal()
        try:
            # Находим все подписки, у которых пришло время списания
            now = datetime.now()
            pending_subscriptions = db.query(models.SubscriptionHistory).filter(
                models.SubscriptionHistory.status == "active",
                models.SubscriptionHistory.auto_renewal == True,
                models.SubscriptionHistory.card_token != None,
                models.SubscriptionHistory.next_payment_date != None,
                models.SubscriptionHistory.next_payment_date <= now
            ).all()
            
            if pending_subscriptions:
                logger.info(f"💳 Found {len(pending_subscriptions)} pending recurrent payments")
            
            for subscription in pending_subscriptions:
                await self.process_recurrent_payment(db, subscription)
            
            # Проверяем приостановленные подписки, которые нужно возобновить
            await self.process_paused_subscriptions(db)
                
        except Exception as e:
            logger.error(f"Error processing pending payments: {e}")
        finally:
            db.close()
    
    async def process_recurrent_payment(self, db: Session, subscription: models.SubscriptionHistory, recursion_depth: int = 0):
        """Обработка одного рекуррентного платежа
        
        Args:
            db: Database session
            subscription: Subscription to process
            recursion_depth: Current recursion depth (защита от бесконечной рекурсии)
        """
        # Защита от бесконечной рекурсии
        if recursion_depth > 5:
            logger.error(f"⚠️ Max recursion depth reached for subscription {subscription.id}, stopping")
            subscription.auto_renewal = False
            subscription.status = "cancelled"
            db.commit()
            return
            
        try:
            user = db.query(models.User).filter(models.User.user_id == subscription.user_id).first()
            if not user:
                logger.error(f"User not found: {subscription.user_id}")
                return
            
            # Определяем сумму и тариф для списания
            if subscription.original_tariff_id:
                target_tariff = db.query(models.Tariff).filter(
                    models.Tariff.id == subscription.original_tariff_id
                ).first()
            else:
                target_tariff = db.query(models.Tariff).filter(
                    models.Tariff.id == subscription.tariff_id
                ).first()
            
            if not target_tariff:
                logger.error(f"Target tariff not found for subscription {subscription.id}")
                return
            
            amount = target_tariff.price
            
            logger.info(f"💳 Processing recurrent payment:")
            logger.info(f"   User: {subscription.user_id}")
            logger.info(f"   Amount: {amount}₽")
            logger.info(f"   Tariff: {target_tariff.name}")
            logger.info(f"   Token: {subscription.card_token[:20]}...")
            
            # Списываем деньги через CloudPayments
            cp_client = get_cloudpayments_client(test_mode=False)
            result = cp_client.charge_token(
                amount=amount,
                currency="RUB",
                account_id=subscription.user_id,
                token=subscription.card_token,
                email="gemerdd@gmail.com",
                description=f"InstardingBot - {target_tariff.name}"
            )
            
            if result.get("Success"):
                logger.info(f"✅ Recurrent payment successful!")
                
                # Создаём запись о платеже
                payment = models.Payment(
                    user_id=subscription.user_id,
                    tariff_id=target_tariff.id,
                    amount=amount,
                    currency="RUB",
                    payment_method="cloudpayments_recurrent",
                    status="completed",
                    transaction_id=result['Model']['TransactionId'],
                    cloudpayments_transaction_id=result['Model']['TransactionId'],
                    card_token=subscription.card_token,
                    is_recurrent=True,
                    subscription_id=subscription.id,
                    created_at=datetime.now(),
                    paid_at=datetime.now()
                )
                db.add(payment)
                
                # Обновляем подписку пользователя
                user.subscription_end = datetime.now() + timedelta(days=target_tariff.duration_days)
                user.current_tariff_id = target_tariff.id
                
                # Устанавливаем дату следующего платежа
                subscription.next_payment_date = datetime.now() + timedelta(days=10)
                subscription.failed_attempts = 0
                subscription.tariff_id = target_tariff.id
                
                db.commit()
                
                logger.info(f"✅ Subscription updated, next payment: {subscription.next_payment_date}")
                
            else:
                logger.error(f"❌ Recurrent payment failed: {result.get('Message')}")
                
                # Увеличиваем счётчик неудачных попыток
                subscription.failed_attempts = (subscription.failed_attempts or 0) + 1
                subscription.last_payment_attempt = datetime.now()
                
                # Если 3 неудачных попытки - пытаемся понизить тариф
                if subscription.failed_attempts >= 3:
                    logger.warning(f"⚠️ 3 failed attempts, trying to downgrade tariff")
                    downgrade_result = await self.try_downgrade_tariff(db, subscription, target_tariff)
                    
                    # Если тариф был понижен - сразу пытаемся списать с нового тарифа
                    if downgrade_result:
                        logger.info(f"🔄 Immediately retrying payment with downgraded tariff (attempt {recursion_depth + 1})")
                        # Рекурсивно вызываем обработку платежа с новым тарифом
                        await self.process_recurrent_payment(db, subscription, recursion_depth + 1)
                        return  # Выходим, чтобы не делать двойной commit
                else:
                    # Повторная попытка через 1 день
                    subscription.next_payment_date = datetime.now() + timedelta(days=1)
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Error processing recurrent payment for subscription {subscription.id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def process_paused_subscriptions(self, db: Session):
        """Обработка приостановленных подписок - возобновление через 7 дней"""
        try:
            now = datetime.now()
            
            # Находим приостановленные подписки, которые нужно возобновить
            # Приостановка длится 7 дней с момента последней попытки оплаты
            paused_subscriptions = db.query(models.SubscriptionHistory).filter(
                models.SubscriptionHistory.status == "paused",
                models.SubscriptionHistory.auto_renewal == False,
                models.SubscriptionHistory.card_token != None,
                models.SubscriptionHistory.last_payment_attempt != None
            ).all()
            
            for subscription in paused_subscriptions:
                # Проверяем, прошло ли 7 дней с момента приостановки
                pause_end_date = subscription.last_payment_attempt + timedelta(days=7)
                
                if now >= pause_end_date:
                    logger.info(f"⏰ Resuming paused subscription {subscription.id} for user {subscription.user_id}")
                    
                    # Возобновляем подписку
                    subscription.status = "active"
                    subscription.auto_renewal = True
                    subscription.next_payment_date = now  # Сразу пытаемся списать
                    subscription.failed_attempts = 0  # Сбрасываем счётчик неудачных попыток
                    
                    db.commit()
                    
                    # Сразу пытаемся списать платёж
                    await self.process_recurrent_payment(db, subscription)
                    
        except Exception as e:
            logger.error(f"Error processing paused subscriptions: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def try_downgrade_tariff(self, db: Session, subscription: models.SubscriptionHistory, current_tariff: models.Tariff) -> bool:
        """Попытка понизить тариф при неудачной оплате
        
        Returns:
            bool: True если тариф был понижен, False если понижение невозможно
        """
        try:
            # Логика понижения тарифа (из cloudpayments_config.py)
            downgrade_map = {
                "Эксклюзив": "Суточный",
                "Суточный": "Фулл",
                "Фулл": "Эко",
                "Эко": "Демо",  # Добавили Демо как последний вариант
                "Демо": None
            }
            
            downgrade_to = downgrade_map.get(current_tariff.name)
            
            if downgrade_to:
                downgrade_tariff = db.query(models.Tariff).filter(
                    models.Tariff.name == downgrade_to
                ).first()
                
                if downgrade_tariff:
                    logger.info(f"📉 Downgrading from {current_tariff.name} to {downgrade_tariff.name}")
                    
                    # Обновляем подписку на новый тариф
                    subscription.original_tariff_id = downgrade_tariff.id
                    subscription.failed_attempts = 0  # Сбрасываем счётчик для нового тарифа
                    subscription.downgrade_attempts = (subscription.downgrade_attempts or 0) + 1
                    # НЕ устанавливаем next_payment_date - попытка будет немедленно
                    
                    db.commit()
                    logger.info(f"✅ Tariff downgraded, will immediately retry with {downgrade_tariff.price}₽")
                    return True
                else:
                    logger.error(f"Downgrade tariff '{downgrade_to}' not found")
                    return False
            else:
                logger.warning(f"⚠️ Cannot downgrade further, disabling auto-renewal")
                subscription.auto_renewal = False
                subscription.status = "cancelled"
                db.commit()
                return False
                
        except Exception as e:
            logger.error(f"Error downgrading tariff: {e}")
            return False


# Глобальный экземпляр планировщика
_scheduler = None

async def start_recurrent_payments_scheduler():
    """Запуск планировщика рекуррентных платежей"""
    global _scheduler
    if _scheduler is None:
        _scheduler = RecurrentPaymentsScheduler()
        await _scheduler.start()

async def stop_recurrent_payments_scheduler():
    """Остановка планировщика рекуррентных платежей"""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()
        _scheduler = None

if __name__ == "__main__":
    # Тестовый запуск
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_recurrent_payments_scheduler())

