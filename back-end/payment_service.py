"""
Сервис управления платежами через CloudPayments
Реализует логику демо-тарифа и каскадного понижения
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import logging

from cloudpayments_client import CloudPaymentsClient, get_cloudpayments_client
import models
import schemas
import crud

logger = logging.getLogger(__name__)

class PaymentService:
    """Сервис управления платежами"""
    
    def __init__(self, db: Session, test_mode: bool = True):
        self.db = db
        self.cp_client = get_cloudpayments_client(test_mode)
    
    # ===== ПЕРВИЧНЫЕ ПЛАТЕЖИ =====
    
    def process_payment(self, user_id: str, tariff_id: int, card_cryptogram: str,
                       name: str, email: str) -> Dict[str, Any]:
        """
        Обработка платежа с созданием подписки для демо-тарифа
        
        Args:
            user_id: ID пользователя
            tariff_id: ID тарифа
            card_cryptogram: Криптограмма карты от виджета
            name: Имя плательщика
            email: Email плательщика
        """
        try:
            # Получаем тариф
            tariff = crud.get_tariff_by_id(self.db, tariff_id)
            if not tariff:
                return {"success": False, "message": "Тариф не найден"}
            
            # Получаем пользователя
            user = crud.get_user_by_id(self.db, user_id)
            if not user:
                return {"success": False, "message": "Пользователь не найден"}
            
            # Проверяем, есть ли уже активная подписка
            existing_subscription = crud.get_active_subscription_by_user(self.db, user_id)
            if existing_subscription and existing_subscription.auto_renewal:
                # Если есть активная автопродлевающаяся подписка, сначала отменяем её
                logger.info(f"User {user_id} has active subscription, cancelling it before new purchase")
                
                # Отменяем старую подписку в CloudPayments
                if existing_subscription.cloudpayments_subscription_id:
                    self.cp_client.cancel_subscription(existing_subscription.cloudpayments_subscription_id)
                
                # Обновляем статус старой подписки
                existing_subscription.status = "cancelled"
                existing_subscription.auto_renewal = False
                self.db.commit()
            
            # Генерируем ID счета
            invoice_id = f"instarding_{user_id}_{tariff_id}_{int(datetime.now().timestamp())}"
            
            # Создаем запись о платеже
            payment = models.Payment(
                user_id=user_id,
                tariff_id=tariff_id,
                amount=tariff.price,
                currency="RUB",
                payment_method="cloudpayments",
                cloudpayments_invoice_id=invoice_id,
                status="pending"
            )
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)
            
            # Выполняем платеж через CloudPayments
            cp_result = self.cp_client.charge_card(
                amount=tariff.price,
                currency="RUB",
                card_cryptogram=card_cryptogram,
                name=name,
                email=email,
                invoice_id=invoice_id,
                description=f"InstardingBot: {tariff.name}",
                account_id=user_id
            )
            
            if not cp_result.get("Success"):
                # Платеж неудачен
                payment.status = "failed"
                self.db.commit()
                return {
                    "success": False, 
                    "message": cp_result.get("Message", "Ошибка платежа")
                }
            
            # Платеж успешен
            transaction = cp_result.get("Model", {})
            payment.status = "completed"
            payment.paid_at = datetime.now()
            payment.cloudpayments_transaction_id = transaction.get("TransactionId")
            payment.card_token = transaction.get("Token")  # Важно для рекуррентных платежей
            payment.card_first_six = transaction.get("CardFirstSix")
            payment.card_last_four = transaction.get("CardLastFour")
            payment.card_type = transaction.get("CardType")
            
            # Активируем тариф пользователя
            crud.update_user_tariff(self.db, user_id, tariff_id)
            
            # Создаем подписку в истории
            subscription = self._create_subscription_history(
                user_id, tariff, payment.card_token, email
            )
            
            # Для демо-тарифа создаем рекуррентную подписку на 999₽ каждые 10 дней
            if tariff.is_demo and payment.card_token:
                self._setup_demo_recurrent_subscription(
                    user_id, payment.card_token, email, subscription.id
                )
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Платеж успешен. Тариф {tariff.name} активирован",
                "payment_id": payment.id,
                "subscription_id": subscription.id
            }
            
        except Exception as e:
            logger.error(f"Payment processing error: {e}")
            self.db.rollback()
            return {"success": False, "message": "Внутренняя ошибка сервера"}
    
    def _create_subscription_history(self, user_id: str, tariff: models.Tariff, 
                                   card_token: str, email: str) -> models.SubscriptionHistory:
        """Создание записи подписки в истории"""
        start_date = datetime.now()
        end_date = None
        
        if tariff.duration_days:
            end_date = start_date + timedelta(days=tariff.duration_days)
        
        subscription = models.SubscriptionHistory(
            user_id=user_id,
            tariff_id=tariff.id,
            start_date=start_date,
            end_date=end_date,
            status="active",
            card_token=card_token,
            auto_renewal=tariff.is_demo,  # Демо-тариф имеет автопродление
            original_tariff_id=tariff.id if tariff.is_demo else None,
            next_payment_date=start_date + timedelta(days=10) if tariff.is_demo else None
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription
    
    def _setup_demo_recurrent_subscription(self, user_id: str, card_token: str, 
                                         email: str, subscription_history_id: int):
        """Настройка рекуррентной подписки для демо-тарифа"""
        try:
            # Находим тариф "Эксклюзив" (999₽ на 10 дней)
            exclusive_tariff = crud.get_tariff_by_name(self.db, "Эксклюзив")
            if not exclusive_tariff:
                logger.error("Тариф 'Эксклюзив' не найден для рекуррентной подписки")
                return
            
            # Создаем подписку в CloudPayments
            start_date = datetime.now() + timedelta(days=1)  # Через день после демо
            
            cp_result = self.cp_client.create_subscription(
                token=card_token,
                account_id=user_id,
                description=f"InstardingBot: Автопродление после Демо (Эксклюзив - 999₽/10 дней)",
                email=email,
                amount=exclusive_tariff.price,
                currency="RUB",
                interval="Day",
                period=10,  # Каждые 10 дней
                start_date=start_date
            )
            
            if cp_result.get("Success"):
                # Обновляем запись подписки
                subscription = self.db.query(models.SubscriptionHistory).get(subscription_history_id)
                if subscription:
                    subscription.cloudpayments_subscription_id = cp_result["Model"]["Id"]
                    subscription.next_payment_date = start_date
                    self.db.commit()
                    
                logger.info(f"Created recurrent subscription for demo user {user_id}")
            else:
                logger.error(f"Failed to create recurrent subscription: {cp_result.get('Message')}")
                
        except Exception as e:
            logger.error(f"Error setting up demo recurrent subscription: {e}")
    
    # ===== ОБРАБОТКА УВЕДОМЛЕНИЙ =====
    
    def handle_payment_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка уведомления о платеже от CloudPayments
        
        Args:
            notification_data: Данные уведомления
        """
        try:
            transaction_id = notification_data.get("TransactionId")
            status = notification_data.get("Status")
            account_id = notification_data.get("AccountId")
            amount = float(notification_data.get("Amount", 0))
            
            logger.info(f"Payment notification: {transaction_id}, status: {status}, user: {account_id}")
            
            if status == "Completed":
                return self._handle_successful_payment(notification_data)
            elif status == "Declined":
                return self._handle_failed_payment(notification_data)
            
            return {"code": 0}  # OK
            
        except Exception as e:
            logger.error(f"Error handling payment notification: {e}")
            return {"code": 1}  # Error
    
    def _handle_successful_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка успешного платежа"""
        try:
            account_id = data.get("AccountId")
            transaction_id = data.get("TransactionId")
            amount = float(data.get("Amount", 0))
            card_token = data.get("Token")  # ← Токен карты из webhook
            
            logger.info(f"💳 Webhook: Payment successful for user {account_id}, amount {amount}, token: {card_token[:20] if card_token else 'NO TOKEN'}...")
            
            # Находим подписку пользователя
            subscription = self.db.query(models.SubscriptionHistory).filter(
                models.SubscriptionHistory.user_id == account_id,
                models.SubscriptionHistory.status == "active"
            ).order_by(models.SubscriptionHistory.id.desc()).first()
            
            # Если подписки нет - webhook пришёл раньше, чем фронтенд создал подписку
            # Сохраняем данные платежа, подписку создаст фронтенд
            if not subscription:
                logger.warning(f"⚠️ Subscription not found yet, saving payment data for later processing")
                
                # Пытаемся извлечь tariff_id из Data
                tariff_id = None
                data_field = data.get("Data")
                if data_field:
                    try:
                        import json
                        data_json = json.loads(data_field)
                        tariff_id = data_json.get("tariff_id")
                        logger.info(f"📦 Extracted tariff_id from Data: {tariff_id}")
                    except:
                        pass
                
                if not tariff_id:
                    logger.warning(f"⚠️ Could not extract tariff_id, will be set later")
                    # Не создаём платёж, подождём пока фронтенд создаст подписку
                    return {"code": 0}
                
                # Создаём запись о платеже с токеном
                payment = models.Payment(
                    user_id=account_id,
                    tariff_id=tariff_id,
                    amount=amount,
                    currency="RUB",
                    payment_method="cloudpayments",
                    status="completed",
                    transaction_id=str(transaction_id),
                    cloudpayments_transaction_id=str(transaction_id),
                    card_token=card_token,
                    is_recurrent=True if card_token else False,
                    created_at=datetime.now(),
                    paid_at=datetime.now()
                )
                self.db.add(payment)
                self.db.commit()
                logger.info(f"✅ Payment saved with tariff_id={tariff_id}, waiting for subscription creation")
                return {"code": 0}
            
            if subscription:
                # Если это первый платёж и есть токен - настраиваем рекуррент
                if card_token and not subscription.card_token:
                    logger.info(f"🔄 Setting up recurrent subscription with token from webhook")
                    subscription.card_token = card_token
                    subscription.auto_renewal = True
                    
                    # Получаем тариф
                    tariff = crud.get_tariff_by_id(self.db, subscription.tariff_id)
                    
                    # Создаём подписку в CloudPayments
                    if tariff and tariff.name == "Демо":
                        # Для демо: 999₽ через 24 часа
                        exclusive_tariff = self.db.query(models.Tariff).filter(
                            models.Tariff.name == "Эксклюзив"
                        ).first()
                        if exclusive_tariff:
                            start_date = datetime.now() + timedelta(hours=24)
                            try:
                                cp_result = self.cp_client.create_subscription(
                                    token=card_token,
                                    account_id=account_id,
                                    description=f"InstardingBot автоплатёж",
                                    amount=999,
                                    currency="RUB",
                                    interval="Day",
                                    period=10,
                                    start_date=start_date
                                )
                                if cp_result.get("Success"):
                                    subscription.cloudpayments_subscription_id = cp_result['Model']['Id']
                                    subscription.next_payment_date = start_date
                                    subscription.original_tariff_id = exclusive_tariff.id
                                    logger.info(f"✅ Recurrent subscription created: {subscription.cloudpayments_subscription_id}")
                            except Exception as e:
                                logger.error(f"❌ Failed to create recurrent subscription: {e}")
                    
                    # Создаём запись о платеже
                    payment = models.Payment(
                        user_id=account_id,
                        tariff_id=subscription.tariff_id,
                        amount=amount,
                        currency="RUB",
                        payment_method="cloudpayments",
                        status="completed",
                        transaction_id=str(transaction_id),
                        cloudpayments_transaction_id=str(transaction_id),
                        card_token=card_token,
                        is_recurrent=True,
                        subscription_id=subscription.id,
                        created_at=datetime.now(),
                        paid_at=datetime.now()
                    )
                    self.db.add(payment)
                    
                    self.db.commit()
                    logger.info(f"✅ Payment and subscription updated with token")
                
                elif subscription.auto_renewal:
                    # Это рекуррентный платеж
                    self._process_recurrent_payment(subscription, data)
            
            return {"code": 0}
            
        except Exception as e:
            logger.error(f"Error handling successful payment: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"code": 1}
    
    def _handle_failed_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка неудачного платежа"""
        try:
            account_id = data.get("AccountId")
            reason = data.get("Reason", "")
            
            # Находим активную подписку
            subscription = self.db.query(models.SubscriptionHistory).filter(
                models.SubscriptionHistory.user_id == account_id,
                models.SubscriptionHistory.status == "active",
                models.SubscriptionHistory.auto_renewal == True
            ).first()
            
            if subscription:
                subscription.failed_attempts += 1
                subscription.last_payment_attempt = datetime.now()
                
                # После 3 неудачных попыток - каскадное понижение
                if subscription.failed_attempts >= 3:
                    self._cascade_downgrade(subscription)
                else:
                    # Планируем повторную попытку через день
                    subscription.next_payment_date = datetime.now() + timedelta(days=1)
                
                self.db.commit()
            
            return {"code": 0}
            
        except Exception as e:
            logger.error(f"Error handling failed payment: {e}")
            return {"code": 1}
    
    def _process_recurrent_payment(self, subscription: models.SubscriptionHistory, 
                                 payment_data: Dict[str, Any]):
        """Обработка рекуррентного платежа"""
        try:
            amount = float(payment_data.get("Amount", 0))
            transaction_id = payment_data.get("TransactionId")
            
            # Создаем запись о платеже
            payment = models.Payment(
                user_id=subscription.user_id,
                tariff_id=subscription.tariff_id,
                amount=amount,
                currency="RUB",
                payment_method="cloudpayments",
                cloudpayments_transaction_id=transaction_id,
                status="completed",
                paid_at=datetime.now(),
                is_recurrent=True,
                subscription_id=subscription.cloudpayments_subscription_id,
                card_token=subscription.card_token
            )
            self.db.add(payment)
            
            # Обновляем подписку
            subscription.failed_attempts = 0  # Сбрасываем счетчик неудач
            subscription.last_payment_attempt = datetime.now()
            
            # Продлеваем подписку
            if subscription.tariff.duration_days:
                if subscription.end_date:
                    subscription.end_date += timedelta(days=subscription.tariff.duration_days)
                else:
                    subscription.end_date = datetime.now() + timedelta(days=subscription.tariff.duration_days)
            
            # Планируем следующий платеж
            subscription.next_payment_date = datetime.now() + timedelta(days=10)
            
            # Обновляем пользователя
            crud.update_user_tariff(self.db, subscription.user_id, subscription.tariff_id)
            
            self.db.commit()
            
            logger.info(f"Processed recurrent payment for user {subscription.user_id}: {amount}₽")
            
        except Exception as e:
            logger.error(f"Error processing recurrent payment: {e}")
            self.db.rollback()
    
    def _cascade_downgrade(self, subscription: models.SubscriptionHistory):
        """Каскадное понижение тарифа при неудачных платежах"""
        try:
            current_tariff = subscription.tariff
            user_id = subscription.user_id
            
            # Определяем следующий тариф по убыванию цены
            downgrade_tariff = self._get_downgrade_tariff(current_tariff.price)
            
            if downgrade_tariff:
                logger.info(f"Downgrading user {user_id} from {current_tariff.name} to {downgrade_tariff.name}")
                
                # Отменяем текущую подписку в CloudPayments
                if subscription.cloudpayments_subscription_id:
                    self.cp_client.cancel_subscription(subscription.cloudpayments_subscription_id)
                
                # Создаем новую подписку на пониженный тариф
                cp_result = self.cp_client.create_subscription(
                    token=subscription.card_token,
                    account_id=user_id,
                    description=f"InstardingBot: {downgrade_tariff.name} (понижение тарифа)",
                    email="",  # Email можно получить из пользователя
                    amount=downgrade_tariff.price,
                    currency="RUB",
                    interval="Day",
                    period=10,
                    start_date=datetime.now() + timedelta(days=1)
                )
                
                if cp_result.get("Success"):
                    # Обновляем подписку
                    subscription.tariff_id = downgrade_tariff.id
                    subscription.cloudpayments_subscription_id = cp_result["Model"]["Id"]
                    subscription.failed_attempts = 0
                    subscription.downgrade_attempts += 1
                    subscription.next_payment_date = datetime.now() + timedelta(days=1)
                    
                    # Обновляем тариф пользователя
                    crud.update_user_tariff(self.db, user_id, downgrade_tariff.id)
                    
                    self.db.commit()
                else:
                    logger.error(f"Failed to create downgrade subscription: {cp_result.get('Message')}")
                    # Если не удалось создать новую подписку, останавливаем
                    subscription.status = "cancelled"
                    subscription.auto_renewal = False
                    self.db.commit()
            else:
                # Нет тарифа для понижения - останавливаем подписку
                logger.info(f"No downgrade tariff available for user {user_id}, stopping subscription")
                subscription.status = "cancelled"
                subscription.auto_renewal = False
                
                if subscription.cloudpayments_subscription_id:
                    self.cp_client.cancel_subscription(subscription.cloudpayments_subscription_id)
                
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error in cascade downgrade: {e}")
            self.db.rollback()
    
    def _get_downgrade_tariff(self, current_price: float) -> Optional[models.Tariff]:
        """Получение тарифа для понижения"""
        # Порядок понижения: Эксклюзив (999) -> Суточный (499) -> Фулл (349) -> Эко (249)
        downgrade_prices = [499.0, 349.0, 249.0]  # Исключаем демо (19) и комбо
        
        for price in downgrade_prices:
            if price < current_price:
                tariff = self.db.query(models.Tariff).filter(
                    models.Tariff.price == price,
                    models.Tariff.is_active == True,
                    models.Tariff.duration_days.isnot(None)  # Только тарифы с временными рамками
                ).first()
                
                if tariff:
                    return tariff
        
        return None
    
    # ===== УПРАВЛЕНИЕ ПОДПИСКАМИ =====
    
    def pause_subscription(self, user_id: str) -> Dict[str, Any]:
        """Приостановка подписки"""
        try:
            from datetime import datetime
            
            subscription = self.db.query(models.SubscriptionHistory).filter(
                models.SubscriptionHistory.user_id == user_id,
                models.SubscriptionHistory.status == "active",
                models.SubscriptionHistory.auto_renewal == True
            ).first()
            
            if not subscription:
                return {"success": False, "message": "Активная подписка не найдена"}
            
            # Отменяем подписку в CloudPayments (временно)
            if subscription.cloudpayments_subscription_id:
                cp_result = self.cp_client.cancel_subscription(subscription.cloudpayments_subscription_id)
                if not cp_result.get("Success"):
                    logger.error(f"Failed to cancel CloudPayments subscription: {cp_result.get('Message')}")
            
            # Обновляем статус
            subscription.status = "paused"
            subscription.auto_renewal = False
            subscription.pause_days_used += 7
            subscription.last_payment_attempt = datetime.now()  # Сохраняем время приостановки
            
            self.db.commit()
            
            logger.info(f"⏸️ Subscription {subscription.id} paused for 7 days, will resume at {subscription.last_payment_attempt + timedelta(days=7)}")
            
            return {"success": True, "message": "Подписка приостановлена на 7 дней"}
            
        except Exception as e:
            logger.error(f"Error pausing subscription: {e}")
            self.db.rollback()
            return {"success": False, "message": "Ошибка при приостановке подписки"}
    
    def resume_subscription(self, user_id: str) -> Dict[str, Any]:
        """Возобновление подписки"""
        try:
            subscription = self.db.query(models.SubscriptionHistory).filter(
                models.SubscriptionHistory.user_id == user_id,
                models.SubscriptionHistory.status == "paused"
            ).first()
            
            if not subscription:
                return {"success": False, "message": "Приостановленная подписка не найдена"}
            
            # Создаем новую подписку в CloudPayments
            cp_result = self.cp_client.create_subscription(
                token=subscription.card_token,
                account_id=user_id,
                description=f"InstardingBot: {subscription.tariff.name} (возобновление)",
                email="",
                amount=subscription.tariff.price,
                currency="RUB",
                interval="Day",
                period=10,
                start_date=datetime.now() + timedelta(days=1)
            )
            
            if cp_result.get("Success"):
                subscription.status = "active"
                subscription.auto_renewal = True
                subscription.cloudpayments_subscription_id = cp_result["Model"]["Id"]
                subscription.next_payment_date = datetime.now() + timedelta(days=1)
                
                self.db.commit()
                
                return {"success": True, "message": "Подписка возобновлена"}
            else:
                return {"success": False, "message": "Ошибка при возобновлении подписки"}
                
        except Exception as e:
            logger.error(f"Error resuming subscription: {e}")
            self.db.rollback()
            return {"success": False, "message": "Ошибка при возобновлении подписки"}
    
    def cancel_subscription(self, user_id: str) -> Dict[str, Any]:
        """Полная отмена подписки"""
        try:
            subscription = self.db.query(models.SubscriptionHistory).filter(
                models.SubscriptionHistory.user_id == user_id,
                models.SubscriptionHistory.status.in_(["active", "paused"])
            ).first()
            
            if not subscription:
                return {"success": False, "message": "Подписка не найдена"}
            
            # Отменяем подписку в CloudPayments
            if subscription.cloudpayments_subscription_id:
                cp_result = self.cp_client.cancel_subscription(subscription.cloudpayments_subscription_id)
                if not cp_result.get("Success"):
                    logger.error(f"Failed to cancel CloudPayments subscription: {cp_result.get('Message')}")
            
            # Обновляем статус
            subscription.status = "cancelled"
            subscription.auto_renewal = False
            
            # Обновляем пользователя
            user = crud.get_user_by_id(self.db, user_id)
            if user:
                user.is_paid = False
                user.current_tariff_id = None
            
            self.db.commit()
            
            return {"success": True, "message": "Подписка отменена"}
            
        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            self.db.rollback()
            return {"success": False, "message": "Ошибка при отмене подписки"}


    def create_recurrent_subscription(self, user_id: str, tariff_id: int, 
                                      card_token: str, transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Создание рекуррентной подписки после успешной оплаты
        
        Args:
            user_id: ID пользователя
            tariff_id: ID тарифа
            card_token: Токен карты от CloudPayments
            transaction_id: ID транзакции (опционально)
        """
        try:
            # Получаем тариф
            tariff = crud.get_tariff_by_id(self.db, tariff_id)
            if not tariff:
                return {"success": False, "message": "Тариф не найден"}
            
            # Получаем пользователя
            user = crud.get_user_by_id(self.db, user_id)
            if not user:
                return {"success": False, "message": "Пользователь не найден"}
            
            # Определяем параметры следующего платежа
            if tariff.name == "Демо":
                # Для демо: 19₽ сейчас, 999₽ через 24 часа
                next_amount = 999
                next_period = 10
                start_date = datetime.now() + timedelta(hours=24)
                # Получаем ID тарифа Эксклюзив
                exclusive_tariff = self.db.query(models.Tariff).filter(
                    models.Tariff.name == "Эксклюзив"
                ).first()
                next_tariff_id = exclusive_tariff.id if exclusive_tariff else tariff_id
            elif tariff.name == "Эксклюзив":
                # Для эксклюзива: 999₽ каждые 10 дней
                next_amount = 999
                next_period = 10
                start_date = datetime.now() + timedelta(days=10)
                next_tariff_id = tariff_id
            else:
                # Для остальных тарифов - без автопродления, просто активируем
                logger.info(f"Tariff {tariff.name} does not support auto-renewal, activating as regular subscription")
                return self.activate_subscription_simple(user_id, tariff_id, transaction_id)
            
            logger.info(f"Creating recurrent subscription for user {user_id}, tariff {tariff.name}, next amount: {next_amount}₽")
            
            # Создаём подписку в CloudPayments
            try:
                cp_result = self.cp_client.create_subscription(
                    token=card_token,
                    account_id=user_id,
                    description=f"InstardingBot автоплатёж",
                    amount=next_amount,
                    currency="RUB",
                    interval="Day",
                    period=next_period,
                    start_date=start_date
                )
                
                if not cp_result.get("Success"):
                    logger.error(f"Failed to create subscription in CloudPayments: {cp_result}")
                    # Активируем обычную подписку без автопродления
                    return self.activate_subscription_simple(user_id, tariff_id, transaction_id)
                
                subscription_id = cp_result['Model']['Id']
                logger.info(f"CloudPayments subscription created: {subscription_id}")
                
            except Exception as e:
                logger.error(f"Error creating subscription in CloudPayments: {e}")
                # В случае ошибки активируем обычную подписку
                return self.activate_subscription_simple(user_id, tariff_id, transaction_id)
            
            # Создаём запись о платеже
            payment = models.Payment(
                user_id=user_id,
                tariff_id=tariff_id,
                amount=tariff.price,
                currency="RUB",
                payment_method="cloudpayments",
                status="completed",
                transaction_id=transaction_id or f"manual_{user_id}_{int(datetime.now().timestamp())}",
                cloudpayments_transaction_id=transaction_id,
                card_token=card_token,
                is_recurrent=True,
                created_at=datetime.now(),
                paid_at=datetime.now()
            )
            self.db.add(payment)
            self.db.flush()  # Получаем ID платежа
            
            # Активируем подписку пользователя
            user.is_paid = True
            user.current_tariff_id = tariff_id
            user.subscription_start = datetime.now()
            
            if tariff.duration_days:
                user.subscription_end = datetime.now() + timedelta(days=tariff.duration_days)
            else:
                user.subscription_end = None
            
            self.db.commit()
            
            # Создаём запись в истории с CloudPayments данными
            subscription_history = models.SubscriptionHistory(
                user_id=user_id,
                tariff_id=tariff_id,
                start_date=datetime.now(),
                end_date=user.subscription_end,
                auto_renewal=True,
                cloudpayments_subscription_id=subscription_id,
                card_token=card_token,
                next_payment_date=start_date,
                original_tariff_id=next_tariff_id,
                status="active"
            )
            self.db.add(subscription_history)
            
            # Связываем платеж с подпиской
            payment.subscription_id = subscription_history.id
            
            self.db.commit()
            
            logger.info(f"Created recurrent subscription for user {user_id}: CP ID {subscription_id}")
            
            return {
                "success": True,
                "message": f"Подписка '{tariff.name}' активирована с автопродлением!"
            }
            
        except Exception as e:
            logger.error(f"Error creating recurrent subscription: {e}")
            self.db.rollback()
            return {"success": False, "message": f"Ошибка создания подписки: {str(e)}"}
    
    def activate_subscription_simple(self, user_id: str, tariff_id: int, 
                                    transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Простая активация подписки без автопродления (fallback)
        """
        try:
            tariff = crud.get_tariff_by_id(self.db, tariff_id)
            if not tariff:
                return {"success": False, "message": "Тариф не найден"}
            
            user = crud.get_user_by_id(self.db, user_id)
            if not user:
                return {"success": False, "message": "Пользователь не найден"}
            
            # Проверяем, есть ли уже платёж от webhook (с токеном)
            # Ищем последний платёж с токеном для этого пользователя и тарифа
            existing_payment = self.db.query(models.Payment).filter(
                models.Payment.user_id == user_id,
                models.Payment.tariff_id == tariff_id,
                models.Payment.status == "completed",
                models.Payment.card_token != None
            ).order_by(models.Payment.id.desc()).first()
            
            if existing_payment:
                # Webhook уже создал платёж с токеном - используем его
                logger.info(f"✅ Found existing payment with token from webhook: {existing_payment.id}")
                payment = existing_payment
                card_token = payment.card_token
            else:
                # Создаём новый платёж без токена
                payment = models.Payment(
                    user_id=user_id,
                    tariff_id=tariff_id,
                    amount=tariff.price,
                    currency="RUB",
                    payment_method="cloudpayments",
                    status="completed",
                    transaction_id=transaction_id or f"manual_{user_id}_{int(datetime.now().timestamp())}",
                    cloudpayments_transaction_id=transaction_id,
                    is_recurrent=False,
                    created_at=datetime.now(),
                    paid_at=datetime.now()
                )
                self.db.add(payment)
                card_token = None
            
            self.db.flush()  # Получаем ID платежа
            
            # Активируем подписку
            user.is_paid = True
            user.current_tariff_id = tariff_id
            user.subscription_start = datetime.now()
            
            if tariff.duration_days:
                user.subscription_end = datetime.now() + timedelta(days=tariff.duration_days)
            else:
                user.subscription_end = None
            
            # Для комбо тарифов
            if tariff.name.startswith("Комбо"):
                if "5" in tariff.name:
                    user.remaining_requests = 5
                elif "10" in tariff.name:
                    user.remaining_requests = 10
            else:
                user.remaining_requests = None
            
            self.db.commit()
            
            # Создаём запись в истории
            subscription_history = models.SubscriptionHistory(
                user_id=user_id,
                tariff_id=tariff_id,
                start_date=datetime.now(),
                end_date=user.subscription_end,
                auto_renewal=bool(card_token),  # Если есть токен - включаем автопродление
                card_token=card_token,
                status="active"
            )
            self.db.add(subscription_history)
            self.db.flush()
            
            # Связываем платеж с подпиской
            payment.subscription_id = subscription_history.id
            
            # Если есть токен - настраиваем автоматические рекуррентные платежи
            if card_token and tariff.name == "Демо":
                logger.info(f"🔄 Setting up recurrent payments with token from webhook")
                try:
                    exclusive_tariff = self.db.query(models.Tariff).filter(
                        models.Tariff.name == "Эксклюзив"
                    ).first()
                    if exclusive_tariff:
                        # Устанавливаем дату следующего платежа (через 24 часа)
                        next_payment_date = datetime.now() + timedelta(hours=24)
                        
                        # Сохраняем информацию о рекуррентной подписке
                        subscription_history.next_payment_date = next_payment_date
                        subscription_history.original_tariff_id = exclusive_tariff.id
                        # CloudPayments не создаёт подписки через API, используем токен для прямых платежей
                        subscription_history.cloudpayments_subscription_id = f"manual_{user_id}_{int(datetime.now().timestamp())}"
                        
                        logger.info(f"✅ Recurrent payments configured:")
                        logger.info(f"   Next payment: {next_payment_date}")
                        logger.info(f"   Amount: 999₽")
                        logger.info(f"   Target tariff: {exclusive_tariff.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to configure recurrent payments: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            self.db.commit()
            
            message = f"Подписка '{tariff.name}' успешно активирована!"

            
            return {
                "success": True,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error activating subscription: {e}")
            self.db.rollback()
            return {"success": False, "message": str(e)}

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def get_payment_service(db: Session, test_mode: bool = True) -> PaymentService:
    """Получение экземпляра сервиса платежей"""
    return PaymentService(db, test_mode)
