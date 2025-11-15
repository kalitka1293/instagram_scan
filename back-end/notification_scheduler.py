"""
Планировщик уведомлений для InstardingBot
Система прогревающих уведомлений о лайках и подписчиках
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import random

from config import (
    NOTIFICATIONS_ENABLED, 
    NOTIFICATION_DELAY_SHORT, 
    NOTIFICATION_DELAY_LONG,
    MINI_APP_URL
)
from database import SessionLocal
from telegram_sender import get_broadcast_manager
import crud
import models

# Настройка логирования
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class NotificationScheduler:
    """Планировщик уведомлений"""
    
    def __init__(self):
        self.running = False
        self.check_interval = 60  # Проверяем каждую минуту
        
    async def start(self):
        """Запуск планировщика"""
        if not NOTIFICATIONS_ENABLED:
            logger.info("Notifications are disabled in config")
            return
            
        logger.info("Starting notification scheduler...")
        self.running = True
        
        try:
            while self.running:
                await self.process_scheduled_notifications()
                await asyncio.sleep(self.check_interval)
                
        except asyncio.CancelledError:
            logger.info("Notification scheduler was cancelled")
        except Exception as e:
            logger.error(f"Error in notification scheduler: {e}")
        finally:
            logger.info("Notification scheduler stopped")
    
    async def stop(self):
        """Остановка планировщика"""
        logger.info("Stopping notification scheduler...")
        self.running = False
    
    async def process_scheduled_notifications(self):
        """Обработка запланированных уведомлений"""
        db = SessionLocal()
        try:
            # Получаем уведомления, которые нужно отправить
            now = datetime.now()
            notifications = db.query(models.NotificationSchedule).filter(
                models.NotificationSchedule.scheduled_time <= now,
                models.NotificationSchedule.sent == False,
                models.NotificationSchedule.retry_count < 3
            ).all()
            
            for notification in notifications:
                await self.send_notification(db, notification)
                
        except Exception as e:
            logger.error(f"Error processing scheduled notifications: {e}")
        finally:
            db.close()
    
    async def send_notification(self, db, notification: models.NotificationSchedule):
        """Отправка уведомления"""
        try:
            broadcast_manager = get_broadcast_manager()
            if not broadcast_manager:
                logger.warning("Broadcast manager not initialized")
                return
            
            # Подготавливаем данные сообщения
            message_data = {
                "text": notification.message_text,
                "inline_button": {
                    "text": notification.button_text or "Открыть InstardingBot",
                    "url": notification.button_url or MINI_APP_URL
                }
            }
            
            # Отправляем уведомление
            result = await broadcast_manager.sender.send_message_async(
                notification.user_id, 
                message_data
            )
            
            if result.get("success"):
                # Помечаем как отправленное
                notification.sent = True
                notification.sent_at = datetime.now()
                logger.info(f"Sent notification to {notification.user_id}: {notification.notification_type}")
            else:
                # Увеличиваем счетчик попыток
                notification.retry_count += 1
                notification.error_message = result.get("error", "Unknown error")
                logger.error(f"Failed to send notification to {notification.user_id}: {result.get('error')}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {e}")
            notification.retry_count += 1
            notification.error_message = str(e)
            db.commit()


# Функции для регистрации активности и планирования уведомлений

async def register_profile_parse(user_id: str, username: str):
    """Регистрация парсинга профиля и планирование всех прогревающих уведомлений"""
    if not NOTIFICATIONS_ENABLED:
        return
        
    db = SessionLocal()
    try:
        # Регистрируем активность
        activity = models.UserActivity(
            user_id=user_id,
            activity_type="profile_parse",
            extra_data={"username": username}
        )
        db.add(activity)
        
        # Планируем все прогревающие уведомления
        await schedule_like_notification(db, user_id, username)  # 5-10 минут
        await schedule_follower_notification(db, user_id, username)  # 24 часа
        await schedule_message_notification(db, user_id, username)  # 48 часов
        await schedule_observer_notification(db, user_id, username)  # 72 часа
        await schedule_activity_notification(db, user_id, username)  # 96 часов
        
        db.commit()
        logger.info(f"Registered profile parse for {user_id}: {username} with all warming notifications")
        
    except Exception as e:
        logger.error(f"Error registering profile parse: {e}")
        db.rollback()
    finally:
        db.close()

async def schedule_like_notification(db, user_id: str, username: str):
    """Планирование уведомления о лайках (5-10 минут после выхода из приложения)"""
    try:
        # Случайная задержка от 5 до 10 минут
        delay_minutes = random.randint(5, 10)
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        # Текст уведомления
        message_text = f"Профиль {username} поставил новый лайк"
        
        notification = models.NotificationSchedule(
            user_id=user_id,
            notification_type="like",
            scheduled_time=scheduled_time,
            profile_username=username,
            message_text=message_text,
            button_text="Посмотреть",
            button_url=MINI_APP_URL
        )
        
        db.add(notification)
        logger.info(f"Scheduled like notification for {user_id} in {delay_minutes} minutes")
        
    except Exception as e:
        logger.error(f"Error scheduling like notification: {e}")

async def schedule_follower_notification(db, user_id: str, username: str):
    """Планирование уведомления о наблюдателе (2 часа после запуска приложения)"""
    try:
        # Задержка 2 часа
        scheduled_time = datetime.now() + timedelta(hours=2)
        
        # Текст уведомления
        message_text = f"На страничке {username} появился новый наблюдатель"
        
        notification = models.NotificationSchedule(
            user_id=user_id,
            notification_type="follower",
            scheduled_time=scheduled_time,
            profile_username=username,
            message_text=message_text,
            button_text="Узнать",
            button_url=MINI_APP_URL
        )
        
        db.add(notification)
        logger.info(f"Scheduled follower notification for {user_id} in 24 hours")
        
    except Exception as e:
        logger.error(f"Error scheduling follower notification: {e}")

async def schedule_message_notification(db, user_id: str, username: str):
    """Планирование уведомления о сообщении (48 часов после запуска приложения)"""
    try:
        # Задержка 48 часов
        scheduled_time = datetime.now() + timedelta(hours=48)
        
        # Текст уведомления
        message_text = f"Профиль {username} отправил сообщение пользователю, на которого не подписан"
        
        notification = models.NotificationSchedule(
            user_id=user_id,
            notification_type="message",
            scheduled_time=scheduled_time,
            profile_username=username,
            message_text=message_text,
            button_text="Посмотреть",
            button_url=MINI_APP_URL
        )
        
        db.add(notification)
        logger.info(f"Scheduled message notification for {user_id} in 48 hours")
        
    except Exception as e:
        logger.error(f"Error scheduling message notification: {e}")

async def schedule_observer_notification(db, user_id: str, username: str):
    """Планирование уведомления о наблюдателе на своей странице (72 часа после запуска приложения)"""
    try:
        # Задержка 72 часа
        scheduled_time = datetime.now() + timedelta(hours=72)
        
        # Текст уведомления
        message_text = "На вашей страничке появился новый наблюдатель"
        
        notification = models.NotificationSchedule(
            user_id=user_id,
            notification_type="observer",
            scheduled_time=scheduled_time,
            profile_username=username,
            message_text=message_text,
            button_text="Узнать",
            button_url=MINI_APP_URL
        )
        
        db.add(notification)
        logger.info(f"Scheduled observer notification for {user_id} in 72 hours")
        
    except Exception as e:
        logger.error(f"Error scheduling observer notification: {e}")

async def schedule_activity_notification(db, user_id: str, username: str):
    """Планирование уведомления о повышенной активности (96 часов после запуска приложения)"""
    try:
        # Задержка 96 часов
        scheduled_time = datetime.now() + timedelta(hours=96)
        
        # Текст уведомления
        message_text = f"В профиле {username} замечена повышенная активность"
        
        notification = models.NotificationSchedule(
            user_id=user_id,
            notification_type="activity",
            scheduled_time=scheduled_time,
            profile_username=username,
            message_text=message_text,
            button_text="Узнать",
            button_url=MINI_APP_URL
        )
        
        db.add(notification)
        logger.info(f"Scheduled activity notification for {user_id} in 96 hours")
        
    except Exception as e:
        logger.error(f"Error scheduling activity notification: {e}")

async def register_app_exit(user_id: str):
    """Регистрация выхода из приложения"""
    if not NOTIFICATIONS_ENABLED:
        return
        
    db = SessionLocal()
    try:
        activity = models.UserActivity(
            user_id=user_id,
            activity_type="app_exit"
        )
        db.add(activity)
        db.commit()
        logger.info(f"Registered app exit for {user_id}")
        
    except Exception as e:
        logger.error(f"Error registering app exit: {e}")
        db.rollback()
    finally:
        db.close()

async def register_app_start(user_id: str):
    """Регистрация запуска приложения"""
    if not NOTIFICATIONS_ENABLED:
        return
        
    db = SessionLocal()
    try:
        activity = models.UserActivity(
            user_id=user_id,
            activity_type="app_start"
        )
        db.add(activity)
        db.commit()
        logger.info(f"Registered app start for {user_id}")
        
    except Exception as e:
        logger.error(f"Error registering app start: {e}")
        db.rollback()
    finally:
        db.close()

def get_user_activity_stats(user_id: str, days: int = 7) -> Dict[str, Any]:
    """Получение статистики активности пользователя"""
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)
        
        activities = db.query(models.UserActivity).filter(
            models.UserActivity.user_id == user_id,
            models.UserActivity.timestamp >= since
        ).all()
        
        stats = {
            "total_activities": len(activities),
            "profile_parses": len([a for a in activities if a.activity_type == "profile_parse"]),
            "app_starts": len([a for a in activities if a.activity_type == "app_start"]),
            "app_exits": len([a for a in activities if a.activity_type == "app_exit"]),
            "last_activity": max([a.timestamp for a in activities]) if activities else None
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting user activity stats: {e}")
        return {}
    finally:
        db.close()


# Глобальный экземпляр планировщика
_scheduler_instance: Optional[NotificationScheduler] = None
_scheduler_task: Optional[asyncio.Task] = None

async def start_scheduler():
    """Запуск планировщика уведомлений"""
    global _scheduler_instance, _scheduler_task
    
    if not NOTIFICATIONS_ENABLED:
        logger.info("Notifications disabled, scheduler not started")
        return
    
    if _scheduler_instance and _scheduler_instance.running:
        logger.warning("Scheduler is already running")
        return
    
    try:
        _scheduler_instance = NotificationScheduler()
        _scheduler_task = asyncio.create_task(_scheduler_instance.start())
        
        logger.info("✅ Notification scheduler started successfully")
        
        # Ждем завершения задачи
        await _scheduler_task
        
    except Exception as e:
        logger.error(f"❌ Error starting notification scheduler: {e}")
        raise

async def stop_scheduler():
    """Остановка планировщика уведомлений"""
    global _scheduler_instance, _scheduler_task
    
    if _scheduler_instance:
        await _scheduler_instance.stop()
        _scheduler_instance = None
    
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
    
    logger.info("✅ Notification scheduler stopped")

def is_scheduler_running() -> bool:
    """Проверка, запущен ли планировщик"""
    return _scheduler_instance is not None and _scheduler_instance.running

