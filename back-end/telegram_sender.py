"""
Модуль для массовых рассылок в Telegram
Поддерживает отправку текста, фото, видео и инлайн кнопок
"""

import requests
import json
import asyncio
import aiohttp
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramSender:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
    async def send_message_async(self, chat_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Асинхронная отправка сообщения"""
        
        url = f"{self.base_url}/sendMessage"
        
        # Базовая структура сообщения
        payload = {
            "chat_id": chat_id,
            "parse_mode": "HTML"
        }
        
        # Добавляем текст
        if message_data.get('text'):
            payload['text'] = message_data['text']
        
        # Добавляем инлайн клавиатуру
        if message_data.get('inline_button'):
            button_data = message_data['inline_button']
            payload['reply_markup'] = {
                "inline_keyboard": [[{
                    "text": button_data['text'],
                    "url": button_data['url']
                }]]
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('ok'):
                        return {"success": True, "message_id": result['result']['message_id']}
                    else:
                        logger.error(f"Ошибка отправки сообщения: {result}")
                        return {"success": False, "error": result.get('description', 'Unknown error')}
                        
        except Exception as e:
            logger.error(f"Исключение при отправке сообщения: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_photo_async(self, chat_id: str, photo_url: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Асинхронная отправка фото"""
        
        url = f"{self.base_url}/sendPhoto"
        
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "parse_mode": "HTML"
        }
        
        # Добавляем подпись
        if message_data.get('text'):
            payload['caption'] = message_data['text']
        
        # Добавляем инлайн клавиатуру
        if message_data.get('inline_button'):
            button_data = message_data['inline_button']
            payload['reply_markup'] = {
                "inline_keyboard": [[{
                    "text": button_data['text'],
                    "url": button_data['url']
                }]]
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('ok'):
                        return {"success": True, "message_id": result['result']['message_id']}
                    else:
                        logger.error(f"Ошибка отправки фото: {result}")
                        return {"success": False, "error": result.get('description', 'Unknown error')}
                        
        except Exception as e:
            logger.error(f"Исключение при отправке фото: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_video_async(self, chat_id: str, video_url: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Асинхронная отправка видео"""
        
        url = f"{self.base_url}/sendVideo"
        
        payload = {
            "chat_id": chat_id,
            "video": video_url,
            "parse_mode": "HTML"
        }
        
        # Добавляем подпись
        if message_data.get('text'):
            payload['caption'] = message_data['text']
        
        # Добавляем инлайн клавиатуру
        if message_data.get('inline_button'):
            button_data = message_data['inline_button']
            payload['reply_markup'] = {
                "inline_keyboard": [[{
                    "text": button_data['text'],
                    "url": button_data['url']
                }]]
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('ok'):
                        return {"success": True, "message_id": result['result']['message_id']}
                    else:
                        logger.error(f"Ошибка отправки видео: {result}")
                        return {"success": False, "error": result.get('description', 'Unknown error')}
                        
        except Exception as e:
            logger.error(f"Исключение при отправке видео: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_broadcast_async(self, user_ids: List[str], message_data: Dict[str, Any], 
                                 delay_seconds: float = 0.1) -> Dict[str, Any]:
        """Массовая рассылка с контролем скорости"""
        
        results = {
            "total": len(user_ids),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        logger.info(f"Начинаем массовую рассылку для {len(user_ids)} пользователей")
        
        for i, user_id in enumerate(user_ids, 1):
            try:
                # Определяем тип сообщения
                if message_data.get('photo_url'):
                    result = await self.send_photo_async(user_id, message_data['photo_url'], message_data)
                elif message_data.get('video_url'):
                    result = await self.send_video_async(user_id, message_data['video_url'], message_data)
                else:
                    result = await self.send_message_async(user_id, message_data)
                
                if result['success']:
                    results['success'] += 1
                    logger.info(f"✅ {i}/{len(user_ids)}: Отправлено пользователю {user_id}")
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        "user_id": user_id,
                        "error": result['error']
                    })
                    logger.warning(f"❌ {i}/{len(user_ids)}: Ошибка для пользователя {user_id}: {result['error']}")
                
                # Задержка между отправками
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    "user_id": user_id,
                    "error": str(e)
                })
                logger.error(f"❌ {i}/{len(user_ids)}: Исключение для пользователя {user_id}: {e}")
        
        logger.info(f"Рассылка завершена. Успешно: {results['success']}, Ошибок: {results['failed']}")
        return results
    
    def send_broadcast_sync(self, user_ids: List[str], message_data: Dict[str, Any], 
                          delay_seconds: float = 0.1) -> Dict[str, Any]:
        """Синхронная обёртка для массовой рассылки"""
        return asyncio.run(self.send_broadcast_async(user_ids, message_data, delay_seconds))

class BroadcastManager:
    """Менеджер рассылок с интеграцией в базу данных"""
    
    def __init__(self, bot_token: str):
        self.sender = TelegramSender(bot_token)
    
    def get_users_by_criteria(self, db, criteria: str) -> List[str]:
        """Получить список пользователей по критериям"""
        from crud import get_total_users_count, get_users_with_stats
        
        if criteria == "all":
            # Все пользователи
            users = get_users_with_stats(db, page=1, page_size=10000)
            return [user['user']['user_id'] for user in users]
        
        elif criteria == "paid":
            # Только платные пользователи
            users = get_users_with_stats(db, page=1, page_size=10000)
            return [user['user']['user_id'] for user in users if user['has_active_subscription']]
        
        elif criteria == "free":
            # Только бесплатные пользователи
            users = get_users_with_stats(db, page=1, page_size=10000)
            return [user['user']['user_id'] for user in users if not user['has_active_subscription']]
        
        else:
            return []
    
    async def create_broadcast(self, db, broadcast_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать и запустить рассылку"""
        
        # Получаем список пользователей
        criteria = broadcast_data.get('target_criteria', 'all')
        user_ids = broadcast_data.get('selected_users', [])
        
        if not user_ids and criteria:
            user_ids = self.get_users_by_criteria(db, criteria)
        
        if not user_ids:
            return {"success": False, "error": "Не найдены пользователи для рассылки"}
        
        # Формируем данные сообщения
        message_data = {
            "text": broadcast_data.get('text', ''),
            "photo_url": broadcast_data.get('photo_url'),
            "video_url": broadcast_data.get('video_url')
        }
        
        # Добавляем инлайн кнопку если есть
        if broadcast_data.get('button_text') and broadcast_data.get('button_url'):
            message_data['inline_button'] = {
                "text": broadcast_data['button_text'],
                "url": broadcast_data['button_url']
            }
        
        # Запускаем рассылку
        try:
            results = await self.sender.send_broadcast_async(
                user_ids, 
                message_data, 
                delay_seconds=broadcast_data.get('delay_seconds', 0.1)
            )
            
            # Сохраняем результаты в базу (опционально)
            self.save_broadcast_results(db, broadcast_data, results)
            
            return {
                "success": True,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания рассылки: {e}")
            return {"success": False, "error": str(e)}
    
    def save_broadcast_results(self, db, broadcast_data: Dict[str, Any], results: Dict[str, Any]):
        """Сохранить результаты рассылки в базу данных"""
        # Здесь можно добавить сохранение в отдельную таблицу broadcast_history
        # Для простоты пока просто логируем
        logger.info(f"Рассылка завершена: {results}")

# Глобальный экземпляр менеджера рассылок
broadcast_manager = None

def init_broadcast_manager(bot_token: str):
    """Инициализация менеджера рассылок"""
    global broadcast_manager
    broadcast_manager = BroadcastManager(bot_token)
    return broadcast_manager

def get_broadcast_manager() -> Optional[BroadcastManager]:
    """Получить экземпляр менеджера рассылок"""
    return broadcast_manager



