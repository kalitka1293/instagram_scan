#!/usr/bin/env python3
"""
Launcher для InstardingBot с Telegram ботом и уведомлениями
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Добавляем текущую директорию в sys.path
sys.path.insert(0, str(Path(__file__).parent))

from config import check_config, TELEGRAM_BOT_TOKEN, NOTIFICATIONS_ENABLED, MINI_APP_URL
from telegram_bot import start_bot, stop_bot
from notification_scheduler import start_scheduler, stop_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('instarding_bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class InstardingBotLauncher:
    def __init__(self):
        self.running = False
        self.bot = None
        self.scheduler = None
    
    async def start(self):
        """Запуск всей системы"""
        try:
            print("🎉 Запуск InstardingBot с Telegram интеграцией")
            print("=" * 50)
            
            # Проверяем конфигурацию
            if not check_config():
                print("❌ Критические ошибки конфигурации. Остановка.")
                return False
            
            # Проверяем базу данных
            if not await self.check_database():
                print("❌ Проблемы с базой данных. Остановка.")
                return False
            
            self.running = True
            
            # Запускаем компоненты
            tasks = []
            
            # Запускаем Telegram бота
            if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "DEMO_TOKEN":
                print("🤖 Запуск Telegram бота...")
                bot_task = asyncio.create_task(self.run_bot())
                tasks.append(bot_task)
            else:
                print("⚠️ Telegram бот не запущен (токен не найден)")
            
            # Запускаем планировщик уведомлений
            if NOTIFICATIONS_ENABLED:
                print("⏰ Запуск планировщика уведомлений...")
                scheduler_task = asyncio.create_task(self.run_scheduler())
                tasks.append(scheduler_task)
            else:
                print("⚠️ Планировщик уведомлений отключен")
            
            if not tasks:
                print("❌ Нет активных компонентов для запуска")
                return False
            
            print("✅ Все компоненты запущены!")
            print("\n🔧 Управление:")
            print("  - Ctrl+C для остановки")
            print("  - Логи сохраняются в instarding_bot.log")
            print(f"  - Админ панель: http://localhost:8000/admin/")
            print("\n📊 Статус:")
            print(f"  - Telegram бот: {'🟢 Активен' if TELEGRAM_BOT_TOKEN else '🔴 Отключен'}")
            print(f"  - Уведомления: {'🟢 Активны' if NOTIFICATIONS_ENABLED else '🔴 Отключены'}")
            print(f"  - Mini App URL: {MINI_APP_URL}")
            print("=" * 50)
            
            # Ждем завершения всех задач
            await asyncio.gather(*tasks)
            
            return True
            
        except KeyboardInterrupt:
            print("\n🛑 Получен сигнал остановки...")
            await self.stop()
            return True
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            await self.stop()
            return False
    
    async def stop(self):
        """Остановка всех компонентов"""
        self.running = False
        
        print("🛑 Остановка компонентов...")
        
        try:
            await stop_bot()
            await stop_scheduler()
            print("✅ Все компоненты остановлены")
        except Exception as e:
            logger.error(f"⚠️ Ошибка при остановке: {e}")
    
    async def run_bot(self):
        """Запуск Telegram бота"""
        try:
            await start_bot()
        except Exception as e:
            logger.error(f"❌ Ошибка Telegram бота: {e}")
            if self.running:
                print(f"⚠️ Telegram бот упал: {e}")
                print("🔄 Попытка перезапуска через 10 секунд...")
                await asyncio.sleep(10)
                if self.running:
                    await self.run_bot()  # Рекурсивный перезапуск
    
    async def run_scheduler(self):
        """Запуск планировщика уведомлений"""
        try:
            await start_scheduler()
        except Exception as e:
            logger.error(f"❌ Ошибка планировщика: {e}")
            if self.running:
                print(f"⚠️ Планировщик упал: {e}")
                print("🔄 Попытка перезапуска через 10 секунд...")
                await asyncio.sleep(10)
                if self.running:
                    await self.run_scheduler()  # Рекурсивный перезапуск
    
    async def check_database(self):
        """Проверка и подготовка базы данных"""
        try:
            from migrate_db import migrate_database
            
            print("💾 Проверка базы данных...")
            
            if not os.path.exists("instarding_bot.db"):
                print("📋 База данных не найдена, создание...")
            
            success = migrate_database()
            
            if success:
                print("✅ База данных готова")
                return True
            else:
                print("❌ Ошибка подготовки базы данных")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка работы с базой данных: {e}")
            return False

async def main():
    """Главная функция"""
    launcher = InstardingBotLauncher()

    try:
        await launcher.start()
    except Exception as e:
        print(f"❌ Критическая ошибка запуска: {e}")
        sys.exit(1)

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\n👋 До свидания!")
#     except Exception as e:
#         print(f"❌ Фатальная ошибка: {e}")
#         sys.exit(1)
