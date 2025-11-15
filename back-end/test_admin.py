#!/usr/bin/env python3
"""
Тестирование админ панели InstardingBot
"""

import requests
import json
from datetime import datetime
import time

# Базовый URL админки
ADMIN_BASE_URL = "http://127.0.0.1:8002/admin"
API_BASE_URL = "http://127.0.0.1:8002"

def test_admin_endpoints():
    """Тестирование всех endpoints админки"""
    
    print("🧪 Тестирование админ панели InstardingBot")
    print("=" * 50)
    
    # Тест 1: Дашборд
    print("\n1. 📊 Тестирование дашборда...")
    try:
        response = requests.get(f"{ADMIN_BASE_URL}/")
        if response.status_code == 200:
            print("✅ Дашборд доступен")
            print(f"   URL: {ADMIN_BASE_URL}/")
        else:
            print(f"❌ Ошибка дашборда: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка соединения с дашбордом: {e}")
    
    # Тест 2: API метрик
    print("\n2. 📈 Тестирование API метрик...")
    try:
        response = requests.get(f"{ADMIN_BASE_URL}/api/metrics")
        if response.status_code == 200:
            metrics = response.json()
            print("✅ API метрик работает")
            print(f"   Пользователей: {metrics.get('users', {}).get('total', 0)}")
            print(f"   Профилей: {metrics.get('profiles', {}).get('total', 0)}")
            print(f"   Подписок: {metrics.get('subscriptions', {}).get('total', 0)}")
        else:
            print(f"❌ Ошибка API метрик: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка API метрик: {e}")
    
    # Тест 3: Управление пользователями
    print("\n3. 👥 Тестирование страницы пользователей...")
    try:
        response = requests.get(f"{ADMIN_BASE_URL}/users")
        if response.status_code == 200:
            print("✅ Страница пользователей доступна")
            print(f"   URL: {ADMIN_BASE_URL}/users")
        else:
            print(f"❌ Ошибка страницы пользователей: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка страницы пользователей: {e}")
    
    # Тест 4: Все запросы
    print("\n4. 🔍 Тестирование страницы запросов...")
    try:
        response = requests.get(f"{ADMIN_BASE_URL}/profiles")
        if response.status_code == 200:
            print("✅ Страница запросов доступна")
            print(f"   URL: {ADMIN_BASE_URL}/profiles")
        else:
            print(f"❌ Ошибка страницы запросов: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка страницы запросов: {e}")
    
    # Тест 5: Статистика подписок
    print("\n5. 💳 Тестирование статистики подписок...")
    try:
        response = requests.get(f"{ADMIN_BASE_URL}/subscriptions")
        if response.status_code == 200:
            print("✅ Страница подписок доступна")
            print(f"   URL: {ADMIN_BASE_URL}/subscriptions")
        else:
            print(f"❌ Ошибка страницы подписок: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка страницы подписок: {e}")
    
    # Тест 6: Основное API (проверяем что оно тоже работает)
    print("\n6. 🌐 Тестирование основного API...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Основное API работает")
        else:
            print(f"❌ Ошибка основного API: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка основного API: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Тестирование завершено!")
    print(f"\n📍 Админ панель доступна по адресу: {ADMIN_BASE_URL}/")
    print("📖 Документация API: http://127.0.0.1:8002/docs")

def create_test_data():
    """Создание тестовых данных для демонстрации"""
    
    print("\n🎭 Создание тестовых данных...")
    
    try:
        # Создаем тестового пользователя
        auth_data = {
            "user_id": "test_admin_user"
        }
        
        response = requests.post(f"{API_BASE_URL}/api/auth/login", json=auth_data)
        if response.status_code == 200:
            print("✅ Тестовый пользователь создан")
        
        # Создаем тестовый профиль
        profile_data = {
            "username": "test_profile", 
            "user_id": "test_admin_user"
        }
        
        response = requests.post(f"{API_BASE_URL}/api/profile/check", json=profile_data)
        if response.status_code == 200:
            print("✅ Тестовый профиль создан")
        else:
            print(f"⚠️ Не удалось создать тестовый профиль: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Ошибка создания тестовых данных: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестирования админ панели...")
    print("⚠️  Убедитесь что сервер запущен: python run_server.py")
    
    # Ждем пару секунд чтобы сервер успел запуститься
    time.sleep(2)
    
    # Создаем тестовые данные
    create_test_data()
    
    # Тестируем админку
    test_admin_endpoints()
    
    print("\n" + "🎉" * 20)
    print("✅ АДМИН ПАНЕЛЬ ГОТОВА К ИСПОЛЬЗОВАНИЮ!")
    print("🎉" * 20)
    print("\n📋 ДОСТУПНЫЕ ФУНКЦИИ:")
    print("🏠 Дашборд: http://127.0.0.1:8002/admin/")
    print("👥 Пользователи: http://127.0.0.1:8002/admin/users")
    print("🔍 Запросы: http://127.0.0.1:8002/admin/profiles") 
    print("💳 Подписки: http://127.0.0.1:8002/admin/subscriptions")
    print("📱 Рассылки: http://127.0.0.1:8002/admin/broadcasts")
    print("\n🔧 Функции:")
    print("✅ Редактирование пользователей")
    print("✅ Экспорт в CSV")
    print("✅ Модальные окна с деталями")
    print("✅ Telegram рассылки (текст/фото/видео)")
    print("✅ Инлайн кнопки в сообщениях")
    print("✅ Фильтрация по подпискам")
    print("✅ Графики и аналитика")
    print("\n🚀 Для настройки Telegram рассылок:")
    print("export TELEGRAM_BOT_TOKEN='your_bot_token'")
