"""
CloudPayments API клиент для InstardingBot
Поддержка рекуррентных платежей и управления подписками
"""

import requests
import json
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CloudPaymentsClient:
    """Клиент для работы с CloudPayments API"""
    
    def __init__(self, public_id: str, api_secret: str, test_mode: bool = True):
        self.public_id = public_id
        self.api_secret = api_secret
        self.test_mode = test_mode
        
        # API URLs
        if test_mode:
            self.api_url = "https://api.cloudpayments.ru/test"
        else:
            self.api_url = "https://api.cloudpayments.ru"
    
    def _create_auth_header(self) -> str:
        """Создание заголовка авторизации"""
        credentials = f"{self.public_id}:{self.api_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение запроса к CloudPayments API"""
        url = f"{self.api_url}/{endpoint}"
        headers = {
            "Authorization": self._create_auth_header(),
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"🌐 CloudPayments API request to {endpoint}")
            logger.info(f"📦 Request data: {json.dumps(data, indent=2, default=str)}")
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ CloudPayments API {endpoint}: Success={result.get('Success', False)}")
            
            if not result.get('Success'):
                logger.error(f"❌ CloudPayments API {endpoint} failed:")
                logger.error(f"   Message: {result.get('Message', 'No message')}")
                logger.error(f"   Full response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ CloudPayments API error {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"   Response: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    logger.error(f"   Response text: {e.response.text}")
            return {"Success": False, "Message": str(e)}
    
    # ===== ОДНОРАЗОВЫЕ ПЛАТЕЖИ =====
    
    def charge_card(self, amount: float, currency: str, card_cryptogram: str, 
                   name: str, email: str, invoice_id: str, description: str,
                   account_id: str = None) -> Dict[str, Any]:
        """
        Платеж по криптограмме карты
        
        Args:
            amount: Сумма платежа
            currency: Валюта (RUB, USD, EUR)
            card_cryptogram: Криптограмма карты от виджета
            name: Имя плательщика
            email: Email плательщика
            invoice_id: ID счета в вашей системе
            description: Описание платежа
            account_id: ID пользователя в вашей системе
        """
        data = {
            "Amount": amount,
            "Currency": currency,
            "CardCryptogramPacket": card_cryptogram,
            "Name": name,
            "Email": email,
            "InvoiceId": invoice_id,
            "Description": description,
            "RequireConfirmation": False,  # Без 3-D Secure для рекуррентных
            "JsonData": {
                "account_id": account_id,
                "service": "InstardingBot"
            }
        }
        
        return self._make_request("payments/cards/charge", data)
    
    # ===== РЕКУРРЕНТНЫЕ ПЛАТЕЖИ =====
    
    def create_subscription(self, token: str, account_id: str, description: str,
                          email: str, amount: float, currency: str = "RUB",
                          interval: str = "Month", period: int = 1,
                          start_date: datetime = None, max_periods: int = None) -> Dict[str, Any]:
        """
        Создание рекуррентной подписки
        
        Args:
            token: Токен карты (получается после первого платежа)
            account_id: ID пользователя в вашей системе
            description: Описание подписки
            email: Email пользователя
            amount: Сумма платежа
            currency: Валюта
            interval: Интервал (Day, Week, Month, Year)
            period: Период (например, 1 = каждый месяц, 2 = каждые 2 месяца)
            start_date: Дата первого списания (по умолчанию - сейчас)
            max_periods: Максимальное количество платежей (None = бессрочно)
        """
        if start_date is None:
            start_date = datetime.now()
        
        data = {
            "Token": token,
            "AccountId": account_id,
            "Description": description,
            "Email": email,
            "Amount": amount,
            "Currency": currency,
            "RequireConfirmation": False,
            "StartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "Interval": interval,
            "Period": period
        }
        
        if max_periods:
            data["MaxPeriods"] = max_periods
            
        return self._make_request("subscriptions/create", data)
    
    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Получение информации о подписке"""
        data = {"Id": subscription_id}
        return self._make_request("subscriptions/get", data)
    
    def update_subscription(self, subscription_id: str, amount: float = None,
                          description: str = None) -> Dict[str, Any]:
        """
        Изменение подписки
        
        Args:
            subscription_id: ID подписки
            amount: Новая сумма платежа
            description: Новое описание
        """
        data = {"Id": subscription_id}
        
        if amount is not None:
            data["Amount"] = amount
        if description is not None:
            data["Description"] = description
            
        return self._make_request("subscriptions/update", data)
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Отмена подписки"""
        data = {"Id": subscription_id}
        return self._make_request("subscriptions/cancel", data)
    
    def find_subscription(self, account_id: str) -> Dict[str, Any]:
        """Поиск подписки по ID аккаунта"""
        data = {"AccountId": account_id}
        return self._make_request("subscriptions/find", data)
    
    # ===== ПЛАТЕЖИ ПО ТОКЕНУ =====
    
    def charge_token(self, amount: float, currency: str, account_id: str,
                    token: str, email: str, description: str) -> Dict[str, Any]:
        """
        Платеж по сохраненному токену карты
        
        Args:
            amount: Сумма платежа
            currency: Валюта
            account_id: ID пользователя
            token: Токен карты
            email: Email пользователя
            description: Описание платежа
        """
        data = {
            "Amount": amount,
            "Currency": currency,
            "AccountId": account_id,
            "Token": token,
            "Email": email,
            "Description": description,
            "RequireConfirmation": False
        }
        
        return self._make_request("payments/tokens/charge", data)
    
    # ===== УВЕДОМЛЕНИЯ =====
    
    def verify_notification(self, data: Dict[str, Any], hmac_header: str) -> bool:
        """
        Проверка подписи уведомления от CloudPayments
        
        Args:
            data: Данные уведомления
            hmac_header: Заголовок X-Content-HMAC
        """
        # Сортируем ключи и создаем строку для подписи
        sorted_data = dict(sorted(data.items()))
        message = "&".join([f"{k}={v}" for k, v in sorted_data.items()])
        
        # Вычисляем HMAC
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature.lower(), hmac_header.lower())


# ===== КОНФИГУРАЦИЯ =====

def get_cloudpayments_client(test_mode: bool = True) -> CloudPaymentsClient:
    """Получение настроенного клиента CloudPayments"""
    import os
    
    # Боевые credentials CloudPayments
    public_id = os.getenv("CLOUDPAYMENTS_PUBLIC_ID", "pk_844cb2c7d4788dc1a506e33a68b18")
    api_secret = os.getenv("CLOUDPAYMENTS_API_SECRET", "df92b2049ce187ec0ab89d8d547bbf5a")
    
    return CloudPaymentsClient(public_id, api_secret, test_mode)


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def format_amount_for_api(amount_rub: float) -> float:
    """Форматирование суммы для API (в рублях с копейками)"""
    return round(amount_rub, 2)

def generate_invoice_id(user_id: str, tariff_id: int) -> str:
    """Генерация ID счета"""
    timestamp = int(datetime.now().timestamp())
    return f"instarding_{user_id}_{tariff_id}_{timestamp}"

def get_subscription_description(tariff_name: str, duration_days: int = None, 
                               requests_count: int = None) -> str:
    """Генерация описания подписки"""
    if duration_days:
        return f"InstardingBot: {tariff_name} ({duration_days} дней)"
    elif requests_count:
        return f"InstardingBot: {tariff_name} ({requests_count} запросов)"
    else:
        return f"InstardingBot: {tariff_name}"



