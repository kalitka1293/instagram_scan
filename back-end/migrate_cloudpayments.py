"""
Миграция для добавления полей CloudPayments
"""

from sqlalchemy import create_engine, text
from config import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_cloudpayments():
    """Добавляет поля для интеграции с CloudPayments"""
    
    engine = create_engine(DATABASE_URL)
    
    # Миграции для таблицы payments
    payments_migrations = [
        # CloudPayments данные
        "ALTER TABLE payments ADD COLUMN cloudpayments_transaction_id VARCHAR(100)",
        "ALTER TABLE payments ADD COLUMN cloudpayments_invoice_id VARCHAR(100)",
        "ALTER TABLE payments ADD COLUMN card_token VARCHAR(200)",
        
        # Данные карты
        "ALTER TABLE payments ADD COLUMN card_type VARCHAR(20)",
        
        # Рекуррентные платежи
        "ALTER TABLE payments ADD COLUMN is_recurrent BOOLEAN DEFAULT FALSE",
        "ALTER TABLE payments ADD COLUMN subscription_id VARCHAR(100)",
        
        # Обновляем payment_method по умолчанию
        "UPDATE payments SET payment_method = 'cloudpayments' WHERE payment_method IS NULL",
    ]
    
    # Миграции для таблицы subscription_history
    subscription_migrations = [
        # CloudPayments данные
        "ALTER TABLE subscription_history ADD COLUMN cloudpayments_subscription_id VARCHAR(100)",
        "ALTER TABLE subscription_history ADD COLUMN card_token VARCHAR(200)",
        "ALTER TABLE subscription_history ADD COLUMN auto_renewal BOOLEAN DEFAULT FALSE",
        "ALTER TABLE subscription_history ADD COLUMN failed_attempts INTEGER DEFAULT 0",
        "ALTER TABLE subscription_history ADD COLUMN last_payment_attempt TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE subscription_history ADD COLUMN next_payment_date TIMESTAMP WITH TIME ZONE",
        
        # Каскадное понижение тарифа
        "ALTER TABLE subscription_history ADD COLUMN original_tariff_id INTEGER REFERENCES tariffs(id)",
        "ALTER TABLE subscription_history ADD COLUMN downgrade_attempts INTEGER DEFAULT 0",
        
        # Метаданные
        "ALTER TABLE subscription_history ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE",
    ]
    
    # Добавляем поле is_demo в таблицу tariffs если его нет
    tariff_migrations = [
        "ALTER TABLE tariffs ADD COLUMN is_demo BOOLEAN DEFAULT FALSE",
        # Помечаем демо тариф
        "UPDATE tariffs SET is_demo = TRUE WHERE name = 'Демо' OR price = 19.0",
    ]
    
    with engine.connect() as conn:
        # Выполняем миграции для payments
        logger.info("Migrating payments table...")
        for migration in payments_migrations:
            try:
                conn.execute(text(migration))
                logger.info(f"✅ {migration}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    logger.info(f"⏭️  Column already exists: {migration}")
                else:
                    logger.error(f"❌ Error: {migration} - {e}")
        
        # Выполняем миграции для subscription_history
        logger.info("Migrating subscription_history table...")
        for migration in subscription_migrations:
            try:
                conn.execute(text(migration))
                logger.info(f"✅ {migration}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    logger.info(f"⏭️  Column already exists: {migration}")
                else:
                    logger.error(f"❌ Error: {migration} - {e}")
        
        # Выполняем миграции для tariffs
        logger.info("Migrating tariffs table...")
        for migration in tariff_migrations:
            try:
                conn.execute(text(migration))
                logger.info(f"✅ {migration}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    logger.info(f"⏭️  Column already exists: {migration}")
                else:
                    logger.error(f"❌ Error: {migration} - {e}")
        
        # Коммитим изменения
        conn.commit()
        logger.info("🎉 CloudPayments migration completed successfully!")

if __name__ == "__main__":
    migrate_cloudpayments()







