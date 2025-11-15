"""
Telegram бот для InstardingBot с long polling и обработкой команд
Интеграция с Mini App и автоматическое обновление пользователей
"""

import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional
import json

from config import TELEGRAM_BOT_TOKEN, MINI_APP_URL, WELCOME_MESSAGE, WELCOME_BUTTON_TEXT
from database import SessionLocal
import crud
import schemas

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram бот с long polling"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.offset = 0
        
    async def start_session(self):
        """Создание HTTP сессии"""
        self.session = aiohttp.ClientSession()
        
    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
            
    async def make_request(self, method: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Выполнение запроса к Telegram API"""
        if not self.session:
            raise RuntimeError("HTTP session not initialized")
            
        url = f"{self.base_url}/{method}"
        
        try:
            async with self.session.post(url, json=data) as response:
                result = await response.json()
                
                if not result.get('ok'):
                    logger.error(f"Telegram API error: {result}")
                    
                return result
                
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"ok": False, "error": str(e)}
    
    async def get_updates(self, timeout: int = 30) -> Dict[str, Any]:
        """Получение обновлений от Telegram"""
        data = {
            "offset": self.offset,
            "timeout": timeout,
            "allowed_updates": ["message", "callback_query"]
        }
        return await self.make_request("getUpdates", data)
    
    async def send_message(self, chat_id: str, text: str, reply_markup: Dict[str, Any] = None) -> Dict[str, Any]:
        """Отправка сообщения"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
            
        return await self.make_request("sendMessage", data)
    
    async def handle_start_command(self, message: Dict[str, Any]):
        """Обработка команды /start"""
        chat_id = str(message["chat"]["id"])
        user = message.get("from", {})
        
        # Обновляем данные пользователя в базе
        await self.update_user_data(chat_id, user)
        
        # Отправляем расширенное приветственное уведомление
        from telegram_sender import TelegramSender
        from config import TELEGRAM_BOT_TOKEN, MINI_APP_URL
        
        try:
            sender = TelegramSender(TELEGRAM_BOT_TOKEN)
            
            # Текст приветственного сообщения
            welcome_text = (
                "🎉 <b>Добро пожаловать в InstardingBot!</b>\n\n"
                "Я помогу вам анализировать Instagram профили и получать детальную статистику.\n\n"
                "📊 <b>Что я умею:</b>\n"
                "• Анализ профилей Instagram\n"
                "• Статистика подписчиков и подписок\n"
                "• Отслеживание активности\n"
                "• Анализ комментариев\n\n"
                "🚀 Нажмите кнопку ниже, чтобы начать!"
            )
            
            # Кнопка для запуска Mini App
            keyboard = {
                "inline_keyboard": [[
                    {
                        "text": "🚀 Открыть InstardingBot",
                        "url": MINI_APP_URL
                    }
                ]]
            }
            
            await sender.send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=keyboard
            )
            
            logger.info(f"Sent welcome message to user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error sending welcome notification: {e}")
            
            # Fallback: отправляем стандартное сообщение
            reply_markup = {
                "inline_keyboard": [[
                    {
                        "text": WELCOME_BUTTON_TEXT,
                        "url": MINI_APP_URL
                    }
                ]]
            }
            await self.send_message(chat_id, WELCOME_MESSAGE, reply_markup)
    
    async def update_user_data(self, user_id: str, telegram_user: Dict[str, Any]):
        """Обновление данных пользователя из Telegram"""
        db = SessionLocal()
        try:
            # Проверяем, существует ли пользователь
            user = crud.get_user_by_id(db, user_id)
            
            if not user:
                # Создаем нового пользователя
                user_create = schemas.UserCreate(user_id=user_id)
                user = crud.create_user(db, user_create)
                logger.info(f"Created new user: {user_id}")
            
            # Обновляем Telegram данные
            update_data = {
                "first_name": telegram_user.get("first_name"),
                "last_name": telegram_user.get("last_name"),
                "telegram_username": telegram_user.get("username")
            }
            
            # Обновляем пользователя
            for field, value in update_data.items():
                if value is not None:
                    setattr(user, field, value)
            
            user.last_login = datetime.now()
            db.commit()
            
            logger.info(f"Updated user data for {user_id}: {telegram_user.get('first_name', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error updating user data: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def handle_message(self, message: Dict[str, Any]):
        """Обработка входящих сообщений"""
        text = message.get("text", "")
        chat_id = str(message["chat"]["id"])
        
        if text.startswith("/start"):
            await self.handle_start_command(message)
        else:
            # Для других сообщений отправляем кнопку Mini App
            reply_markup = {
                "inline_keyboard": [[
                    {
                        "text": "🚀 Открыть InstardingBot",
                        "web_app": {"url": MINI_APP_URL}
                    }
                ]]
            }
            
            await self.send_message(
                chat_id, 
                "Используйте кнопку ниже для запуска InstardingBot:", 
                reply_markup
            )
    
    async def handle_callback_query(self, callback_query: Dict[str, Any]):
        """Обработка callback запросов"""
        # Пока не используется, но может понадобиться для будущих функций
        pass
    
    async def process_updates(self, updates: list):
        """Обработка списка обновлений"""
        for update in updates:
            try:
                self.offset = max(self.offset, update["update_id"] + 1)
                
                if "message" in update:
                    await self.handle_message(update["message"])
                elif "callback_query" in update:
                    await self.handle_callback_query(update["callback_query"])
                    
            except Exception as e:
                logger.error(f"Error processing update {update.get('update_id')}: {e}")
    
    async def run(self):
        """Основной цикл бота"""
        logger.info("Starting Telegram bot...")
        
        await self.start_session()
        self.running = True
        
        try:
            while self.running:
                try:
                    result = await self.get_updates()
                    
                    if result.get("ok") and result.get("result"):
                        updates = result["result"]
                        if updates:
                            await self.process_updates(updates)
                    
                    # Небольшая пауза между запросами
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error in bot main loop: {e}")
                    await asyncio.sleep(5)  # Ждем перед повтором при ошибке
                    
        except asyncio.CancelledError:
            logger.info("Bot was cancelled")
        finally:
            await self.close_session()
            logger.info("Telegram bot stopped")
    
    async def stop(self):
        """Остановка бота"""
        logger.info("Stopping Telegram bot...")
        self.running = False


# Глобальный экземпляр бота
_bot_instance: Optional[TelegramBot] = None
_bot_task: Optional[asyncio.Task] = None

async def start_bot():
    """Запуск Telegram бота"""
    global _bot_instance, _bot_task
    
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "DEMO_TOKEN":
        logger.warning("Telegram bot token not configured")
        return
    
    if _bot_instance and _bot_instance.running:
        logger.warning("Bot is already running")
        return
    
    try:
        _bot_instance = TelegramBot(TELEGRAM_BOT_TOKEN)
        _bot_task = asyncio.create_task(_bot_instance.run())
        
        logger.info("✅ Telegram bot started successfully")
        
        # Ждем завершения задачи
        await _bot_task
        
    except Exception as e:
        logger.error(f"❌ Error starting Telegram bot: {e}")
        raise

async def stop_bot():
    """Остановка Telegram бота"""
    global _bot_instance, _bot_task
    
    if _bot_instance:
        await _bot_instance.stop()
        _bot_instance = None
    
    if _bot_task and not _bot_task.done():
        _bot_task.cancel()
        try:
            await _bot_task
        except asyncio.CancelledError:
            pass
        _bot_task = None
    
    logger.info("✅ Telegram bot stopped")

def get_bot_instance() -> Optional[TelegramBot]:
    """Получение экземпляра бота"""
    return _bot_instance

def is_bot_running() -> bool:
    """Проверка, запущен ли бот"""
    return _bot_instance is not None and _bot_instance.running

