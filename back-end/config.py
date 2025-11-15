#!/usr/bin/env python3
"""
Конфигурация для InstardingBot
"""

import os

# Telegram Bot
TELEGRAM_BOT_TOKEN = "6808895469:AAGflgBpkFCgpnOTk0zC6MmGyls8YIJ59lc" #os.getenv("TELEGRAM_BOT_TOKEN", "8274235448:AAFKVbU5kkrIs_nS1MhldMt8QQl3AgyLkVU")

# Mini App
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://t.me/insidegram_bot?startapp")

# Уведомления
NOTIFICATIONS_ENABLED = os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true"

# Время задержек для уведомлений (в минутах)
NOTIFICATION_DELAY_SHORT = int(os.getenv("NOTIFICATION_DELAY_SHORT", "7"))  # 5-10 минут
NOTIFICATION_DELAY_LONG = int(os.getenv("NOTIFICATION_DELAY_LONG", "1440"))  # 24 часа

# Приветственное сообщение
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", """🎉 Добро пожаловать в INSIDEGRAM!

❗️Важно: Некоторые профили требуют больше времени для анализа. Обычно это занимает до 1 минуты.

Нажмите кнопку ниже, чтобы начать!""")

WELCOME_BUTTON_TEXT = os.getenv("WELCOME_BUTTON_TEXT", "🚀 Запустить InsideGram")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./instarding_bot.db")

# Debug режим
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Проверка обязательных параметров
def check_config():
    """Проверяет наличие обязательных параметров конфигурации"""
    print(TELEGRAM_BOT_TOKEN)
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ TELEGRAM_BOT_TOKEN не установлен!")
        return False
    
    print("✅ Конфигурация загружена успешно")
    print(f"📱 Mini App URL: {MINI_APP_URL}")
    print(f"🔔 Уведомления: {'включены' if NOTIFICATIONS_ENABLED else 'отключены'}")
    print(f"⏰ Задержки: {NOTIFICATION_DELAY_SHORT}мин / {NOTIFICATION_DELAY_LONG}мин")
    
    return True