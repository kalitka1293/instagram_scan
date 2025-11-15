"""
Конфигурация CloudPayments для InstardingBot
"""

import os
from typing import Dict, Any

# ===== CLOUDPAYMENTS CREDENTIALS =====

# Тестовые данные (для разработки)
TEST_PUBLIC_ID = "pk_test_example"
TEST_API_SECRET = "secret_test_example"

# Продакшн данные (получить в личном кабинете CloudPayments)
PRODUCTION_PUBLIC_ID = os.getenv("CLOUDPAYMENTS_PUBLIC_ID", "pk_844cb2c7d4788dc1a506e33a68b18")
PRODUCTION_API_SECRET = os.getenv("CLOUDPAYMENTS_API_SECRET", "df92b2049ce187ec0ab89d8d547bbf5a")

# Режим работы
TEST_MODE = os.getenv("CLOUDPAYMENTS_TEST_MODE", "true").lower() == "true"

def get_cloudpayments_config() -> Dict[str, Any]:
    """Получение конфигурации CloudPayments"""
    if TEST_MODE:
        return {
            "public_id": TEST_PUBLIC_ID,
            "api_secret": TEST_API_SECRET,
            "test_mode": True,
            "webhook_url": "https://your-domain.com/api/payments/cloudpayments/notification"
        }
    else:
        return {
            "public_id": PRODUCTION_PUBLIC_ID,
            "api_secret": PRODUCTION_API_SECRET,
            "test_mode": False,
            "webhook_url": "https://your-domain.com/api/payments/cloudpayments/notification"
        }

# ===== ТАРИФНАЯ ЛОГИКА =====

# Демо тариф: 19₽ на 1 день, затем 999₽ каждые 10 дней
DEMO_TARIFF = {
    "initial_price": 19.0,
    "initial_duration_hours": 24,
    "recurrent_price": 999.0,
    "recurrent_interval_days": 10,
    "target_tariff_name": "Эксклюзив"
}

# Порядок каскадного понижения тарифов при неуспешных платежах
DOWNGRADE_CASCADE = [
    {"name": "Эксклюзив", "price": 999.0, "downgrade_to": "Суточный"},
    {"name": "Суточный", "price": 499.0, "downgrade_to": "Фулл"},
    {"name": "Фулл", "price": 349.0, "downgrade_to": "Эко"},
    {"name": "Эко", "price": 249.0, "downgrade_to": None}  # Последний уровень
]

def get_downgrade_tariff(current_tariff_name: str) -> str:
    """Получение названия тарифа для понижения"""
    for tariff in DOWNGRADE_CASCADE:
        if tariff["name"] == current_tariff_name:
            return tariff["downgrade_to"]
    return None

# ===== НАСТРОЙКИ УВЕДОМЛЕНИЙ =====

NOTIFICATION_SETTINGS = {
    # За сколько дней до списания уведомлять пользователя
    "notify_before_payment_days": 1,
    
    # Количество попыток повторного списания при неудаче
    "retry_attempts": 3,
    
    # Интервал между попытками (в днях)
    "retry_interval_days": 1,
    
    # Максимальное количество понижений тарифа
    "max_downgrades": 3
}

# ===== WEBHOOKS =====

WEBHOOK_EVENTS = [
    "Pay",      # Успешный платеж
    "Fail",     # Неуспешный платеж
    "Confirm",  # Подтверждение платежа
    "Refund"    # Возврат средств
]

def get_webhook_config() -> Dict[str, Any]:
    """Конфигурация webhook'ов для CloudPayments"""
    config = get_cloudpayments_config()
    
    return {
        "url": config["webhook_url"],
        "events": WEBHOOK_EVENTS,
        "format": "CloudPayments",
        "encoding": "UTF-8"
    }

# ===== ВАЛИДАЦИЯ КОНФИГУРАЦИИ =====

def validate_config() -> bool:
    """Проверка корректности конфигурации"""
    config = get_cloudpayments_config()
    
    if not config["public_id"] or not config["api_secret"]:
        print("❌ CloudPayments credentials not configured!")
        return False
    
    if not TEST_MODE and (not PRODUCTION_PUBLIC_ID or not PRODUCTION_API_SECRET):
        print("❌ Production CloudPayments credentials not set!")
        return False
    
    print("✅ CloudPayments configuration is valid")
    return True

if __name__ == "__main__":
    print("🔧 CloudPayments Configuration")
    print(f"Test Mode: {TEST_MODE}")
    
    config = get_cloudpayments_config()
    print(f"Public ID: {config['public_id']}")
    print(f"API Secret: {'*' * len(config['api_secret'])}")
    print(f"Webhook URL: {config['webhook_url']}")
    
    validate_config()



