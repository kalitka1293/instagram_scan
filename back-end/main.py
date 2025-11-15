from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import requests
import logging

logger = logging.getLogger(__name__)

from asyncRequests.loggingAsync import logger
log2 = logger

import crud
import models
import schemas
from database import SessionLocal, engine, init_db
from instagram_parser_v2 import scrape_profile_basic, generate_user_activities, InstagramParserV2
from admin import admin_router

from main_profile_check import async_work_parsing
from asyncRequests.AsyncRequestAPI import ResilientAPIClient

# Настройки кэширования
PROFILE_CACHE_HOURS = 24  # Время жизни кэша профиля

# Создание таблиц
models.Base.metadata.create_all(bind=engine)

api_client: ResilientAPIClient

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     global api_client
#     api_client = ResilientAPIClient(
#         max_concurrent=10,
#         request_timeout=25
#     )
#
#     yield
#
#     # Shutdown
#     if api_client:
#         await api_client.close()
#
# # Dependency для внедрения клиента в эндпоинты
# async def get_api_client():
#     return api_client

app = FastAPI(
    title="InstardingBot API",
    description="API для анализа Instagram профилей",
    version="1.0.0",
    #lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем админскую панель
app.include_router(admin_router)

# Подключаем статичные файлы
app.mount("/static", StaticFiles(directory="static"), name="static")


# Импорты для Telegram интеграции
import asyncio
import os
from config import check_config, TELEGRAM_BOT_TOKEN
from telegram_sender import init_broadcast_manager

from instagram_parser_v2 import CookieRotator

x = CookieRotator()
@app.get('/testttttttttttttttttt')
async def testttttttt():
    c = x.get_next_cookie()
    print(type(c), c)
    return c
# Импортируем функции Telegram бота и планировщика
try:
    from telegram_bot import start_bot, stop_bot
    TELEGRAM_BOT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Telegram bot не доступен: {e}")
    TELEGRAM_BOT_AVAILABLE = False

try:
    from notification_scheduler import start_scheduler, stop_scheduler
    SCHEDULER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Notification scheduler не доступен: {e}")
    SCHEDULER_AVAILABLE = False

try:
    from recurrent_payments_scheduler import start_recurrent_payments_scheduler, stop_recurrent_payments_scheduler
    RECURRENT_PAYMENTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Recurrent payments scheduler не доступен: {e}")
    RECURRENT_PAYMENTS_AVAILABLE = False

async def start_telegram_bot():
    """Запуск Telegram бота в фоне"""
    if not TELEGRAM_BOT_AVAILABLE:
        print("⚠️ Telegram bot не доступен")
        return
        
    try:
        await start_bot()
    except Exception as e:
        print(f"❌ Ошибка запуска Telegram бота: {e}")

async def start_notification_scheduler():
    """Запуск планировщика уведомлений в фоне"""
    if not SCHEDULER_AVAILABLE:
        print("⚠️ Notification scheduler не доступен")
        return
        
    try:
        await start_scheduler()
    except Exception as e:
        print(f"❌ Ошибка запуска планировщика: {e}")

async def start_recurrent_payments():
    """Запуск планировщика рекуррентных платежей в фоне"""
    if not RECURRENT_PAYMENTS_AVAILABLE:
        print("⚠️ Recurrent payments scheduler не доступен")
        return
        
    try:
        await start_recurrent_payments_scheduler()
    except Exception as e:
        print(f"❌ Ошибка запуска планировщика рекуррентных платежей: {e}")

async def send_welcome_notification(user_id: str):
    """Отправка приветственного уведомления при первом парсинге"""
    try:
        from telegram_sender import TelegramSender
        from config import TELEGRAM_BOT_TOKEN, MINI_APP_URL
        
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "DEMO_TOKEN":
            logger.warning("Telegram bot token не установлен, пропускаем приветственное уведомление")
            return
        
        sender = TelegramSender(TELEGRAM_BOT_TOKEN)
        
        message_data = {
            "text": """🎉 Добро пожаловать в INSIDEGRAM!

❗️Важно: Некоторые профили требуют больше времени для анализа. Обычно это занимает до 1 минуты.

Нажмите кнопку ниже, чтобы начать!""",
            "inline_button": {
                "text": "🚀 Начать анализ",
                "url": MINI_APP_URL
            }
        }
        
        result = await sender.send_message_async(user_id, message_data)
        
        if result.get("success"):
            logger.info(f"✅ Приветственное уведомление отправлено пользователю {user_id}")
        else:
            logger.error(f"❌ Ошибка отправки приветственного уведомления: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"❌ Исключение при отправке приветственного уведомления: {e}")

# Инициализация приложения
@app.on_event("startup")
async def startup_event():
    """Инициализация приложения"""
    print("🚀 Запуск InstardingBot...")
    
    # Инициализируем базу данных
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
    
    # Запускаем воркер парсинга
    try:
        from instagram_parser_v2 import start_worker
        start_worker()
        print("✅ Instagram parser worker started")
    except Exception as e:
        print(f"⚠️ Instagram parser warning: {e}")
    
    # Проверяем конфигурацию
    if not check_config():
        print("⚠️ Проблемы с конфигурацией")
    
    # Инициализируем рассылки (старая система)
    bot_token = TELEGRAM_BOT_TOKEN
    
    if bot_token and bot_token != "DEMO_TOKEN":
        try:
            init_broadcast_manager(bot_token)
            print("✅ Telegram рассылки инициализированы")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации Telegram рассылок: {e}")
    else:
        print("⚠️ TELEGRAM_BOT_TOKEN не установлен, рассылки недоступны")
    
    # Запускаем Telegram бота в фоне
    if TELEGRAM_BOT_AVAILABLE:
        asyncio.create_task(start_telegram_bot())
    
    # Запускаем планировщик уведомлений в фоне
    if SCHEDULER_AVAILABLE:
        asyncio.create_task(start_notification_scheduler())
    
    # Запускаем планировщик рекуррентных платежей в фоне
    if RECURRENT_PAYMENTS_AVAILABLE:
        asyncio.create_task(start_recurrent_payments())

@app.on_event("shutdown") 
async def shutdown_event():
    """Остановка приложения"""
    print("🛑 Остановка InstardingBot...")
    
    try:
        if TELEGRAM_BOT_AVAILABLE:
            await stop_bot()
        if SCHEDULER_AVAILABLE:
            await stop_scheduler()
        if RECURRENT_PAYMENTS_AVAILABLE:
            await stop_recurrent_payments_scheduler()
        print("✅ Все сервисы остановлены")
    except Exception as e:
        print(f"⚠️ Ошибка при остановке: {e}")

# Dependency для получения DB сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from asyncRequests.ProxyManager import proxy_manager



@app.get('/test_my_proxy')
async def test_proxy_my():
    log2.debug('sdf32f')
    print('endpoint test_my_proxy')

    data = {'lol': proxy_manager.get_proxy_resource()}
    data.update(proxy_manager.get_stats())


    return data


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {"message": "InstardingBot API is running"}

@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {"status": "healthy", "message": "API is working correctly"}

# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/api/auth/login", response_model=schemas.AuthResponse)
async def login_user(request: schemas.UserLoginRequest, db: Session = Depends(get_db)):
    """Вход пользователя"""
    try:
        # Проверяем, существует ли пользователь
        user = crud.get_user_by_id(db, request.user_id)
        
        if not user:
            # Создаем нового пользователя
            user_create = schemas.UserCreate(user_id=request.user_id)
            user = crud.create_user(db, user_create)
        
        # Обновляем время последнего входа
        crud.update_user_last_login(db, request.user_id)
        
        return schemas.AuthResponse(
            success=True,
            message="Пользователь успешно авторизован",
            user=schemas.User.model_validate(user)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка авторизации: {str(e)}")

@app.get("/api/auth/user/{user_id}", response_model=schemas.User)
async def get_user_info(user_id: str, db: Session = Depends(get_db)):
    """Получить информацию о пользователе"""
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return schemas.User.model_validate(user)

# ===== INSTAGRAM PROFILE ENDPOINTS =====

@app.post("/api/profile/check", response_model=schemas.ProfileCheckResponse)
async def check_profile(request: schemas.ProfileCheckRequest, db: Session = Depends(get_db)):
    """Анализ Instagram профиля с асинхронной обработкой"""
    try:
        username = request.username.lower().strip().replace("@", "")
        
        # Проверяем, первый ли это парсинг для пользователя (для статистики)
        is_first_parse = False
        if hasattr(request, 'user_id') and request.user_id:
            is_first_parse = crud.is_first_profile_parse(db, request.user_id)
        
        # Регистрируем активность парсинга профиля (только при первом парсинге)
        from notification_scheduler import register_profile_parse
        if hasattr(request, 'user_id') and request.user_id and is_first_parse:
            await register_profile_parse(request.user_id, username)
        
        # Увеличиваем счетчик запросов пользователя
        if request.user_id:
            crud.increment_user_requests(db, request.user_id)
        
        # Инициализируем переменные по умолчанию
        from instagram_parser_v2 import generate_user_activities, generate_posts_data
        user_activities = generate_user_activities([], [])
        fresh_posts_data = await generate_posts_data({
            "posts_count": 10,
            "followers_count": 1000
        })

        # Проверяем кэш
        cached_profile = crud.get_instagram_profile_by_username(db, username)
        
        if cached_profile and crud.is_profile_data_fresh(cached_profile, PROFILE_CACHE_HOURS):
            print(f"✅ Используем кэшированные данные для @{username}")
            
            # Проверяем статус парсинга подписчиков
            if cached_profile.parsing_status == "completed":
                # Получаем взаимных подписчиков из базы
                mutual_followers = crud.get_mutual_followers(db, cached_profile.id)
                followers_data = [
                    {
                        "follower_pk": f.follower_pk,
                        "username": f.username,
                        "full_name": f.full_name,
                        "profile_pic_url": f.profile_pic_url,
                        "is_verified": f.is_verified,
                        "is_private": f.is_private,
                        "has_anonymous_profile_picture": f.has_anonymous_profile_picture,
                        "fbid_v2": f.fbid_v2,
                        "third_party_downloads_enabled": f.third_party_downloads_enabled,
                        "latest_reel_media": f.latest_reel_media
                    }
                    for f in mutual_followers
                ]
                
                # Генерируем активности на основе взаимных подписчиков
                mutual_pks = [f["follower_pk"] for f in followers_data]
                user_activities = generate_user_activities(followers_data, mutual_pks)
            else:
                # Парсинг еще идет, возвращаем базовые данные
                user_activities = generate_user_activities([], [])
            
            # Обновляем данные постов с реальными параметрами профиля
            fresh_posts_data = generate_posts_data({
                "posts_count": cached_profile.posts_count or 10,
                "followers_count": cached_profile.followers_count or 1000
            })
            
            # Проверяем подписку пользователя
            has_subscription = crud.has_active_subscription(db, request.user_id) if request.user_id else False
            
            # ✅ Возвращаем кэшированные данные
            return schemas.ProfileCheckResponse(
                success=True,
                message="Данные профиля получены из кэша",
                profile=schemas.InstagramProfile.model_validate(cached_profile),
                analytics_data=cached_profile.analytics_data,
                posts_data=fresh_posts_data,
                comments_data=cached_profile.comments_data,
                user_activities=schemas.UserActivities(**user_activities),
                has_active_subscription=has_subscription
            )
        
        # Парсим базовую информацию профиля
        print(f"🔍 Парсинг профиля @{username}...")
        scraped_result = await scrape_profile_basic(username) # Основной метод получения данных профиля get_profile
        
        if not scraped_result["success"]:
            raise HTTPException(status_code=404, detail=scraped_result.get("error", "Профиль не найден"))
        
        profile_data = scraped_result["profile"]
        analytics_data = scraped_result["analytics_data"]
        posts_data = scraped_result["posts_data"]
        
        # Запускаем асинхронный парсинг подписчиков
        user_id = profile_data["id"]
        task_id = None
        await async_work_parsing(username, user_id)
        

        # Сохраняем или обновляем профиль в базе
        if cached_profile:
            # Обновляем существующий профиль
            profile_update = schemas.InstagramProfileUpdate(
                full_name=profile_data["full_name"],
                biography=profile_data["biography"],
                external_url=profile_data["external_url"],
                followers_count=profile_data["followers_count"],
                following_count=profile_data["following_count"],
                posts_count=profile_data["posts_count"],
                is_verified=profile_data["is_verified"],
                is_private=profile_data["is_private"],
                is_business=profile_data["is_business"],
                profile_pic_url=profile_data["profile_pic_url"],
                analytics_data=analytics_data,
                posts_data=posts_data
            )
            db_profile = crud.update_instagram_profile(db, username, profile_update)
        else:
            # Создаем новый профиль
            profile_create = schemas.InstagramProfileCreate(
                username=username,
                full_name=profile_data["full_name"],
                biography=profile_data["biography"],
                external_url=profile_data["external_url"],
                followers_count=profile_data["followers_count"],
                following_count=profile_data["following_count"],
                posts_count=profile_data["posts_count"],
                is_verified=profile_data["is_verified"],
                is_private=profile_data["is_private"],
                is_business=profile_data["is_business"],
                profile_pic_url=profile_data["profile_pic_url"],
                analytics_data=analytics_data,
                posts_data=posts_data,
                parsing_status="processing" if task_id else "completed",
                parse_task_id=task_id
            )
            db_profile = crud.create_instagram_profile(db, profile_create)
        
        # Возвращаем базовые данные сразу
        user_activities = generate_user_activities([], [])  # Пустые пока парсинг не завершен
        
        # Проверяем подписку пользователя
        has_subscription = crud.has_active_subscription(db, request.user_id) if request.user_id else False
        
        # Проверяем что профиль был создан успешно
        if not db_profile:
            raise HTTPException(status_code=500, detail="Не удалось сохранить профиль в базу данных")
        
        # Обновляем сессию чтобы получить все данные профиля
        db.refresh(db_profile)
        
        return schemas.ProfileCheckResponse(
            success=True,
            message="Профиль получен, подписчики парсятся в фоне",
            profile=schemas.InstagramProfile.model_validate(db_profile),
            analytics_data=analytics_data,
            posts_data=posts_data,
            comments_data=db_profile.comments_data if db_profile.comments_data else [],
            user_activities=schemas.UserActivities(**user_activities),
            has_active_subscription=has_subscription
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ ПОЛНАЯ ОШИБКА:\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка при анализе профиля: {str(e)}")

@app.get("/api/profile/{username}/analytics")
async def get_profile_analytics(username: str, db: Session = Depends(get_db)):
    """Получить аналитику профиля"""
    cached_profile = crud.get_instagram_profile_by_username(db, username.lower())
    
    if not cached_profile:
        raise HTTPException(status_code=404, detail="Профиль не найден в кэше")
    
    return schemas.AnalyticsResponse(
        success=True,
        analytics_data=cached_profile.analytics_data,
        message="Аналитика профиля получена"
    )

@app.get("/api/profile/{username}/stats")
async def get_profile_stats(username: str, db: Session = Depends(get_db)):
    """Получить статистику профиля"""
    cached_profile = crud.get_instagram_profile_by_username(db, username.lower())
    
    if not cached_profile:
        raise HTTPException(status_code=404, detail="Профиль не найден в кэше")
    
    return schemas.StatsResponse(
        success=True,
        stats_data=cached_profile.stats_data,
        message="Статистика профиля получена"
    )

@app.get("/api/profile/{username}/followers", response_model=schemas.FollowersResponse)
async def get_profile_followers(username: str, db: Session = Depends(get_db)):
    """Получить подписчиков профиля (с проверкой статуса парсинга)"""
    try:
        cached_profile = crud.get_instagram_profile_by_username(db, username.lower())
        
        if not cached_profile:
            raise HTTPException(status_code=404, detail="Профиль не найден")
        
        # Проверяем статус парсинга
        if cached_profile.parsing_status == "completed":
            # Получаем взаимных подписчиков
            mutual_followers = crud.get_mutual_followers(db, cached_profile.id)
            followers_data = [
                {
                    "follower_pk": f.follower_pk,
                    "username": f.username,
                    "full_name": f.full_name,
                    "profile_pic_url": f.profile_pic_url,
                    "is_verified": f.is_verified,
                    "is_private": f.is_private
                }
                for f in mutual_followers
            ]
            
            return schemas.FollowersResponse(
                success=True,
                message="Подписчики получены",
                status="completed",
                followers=followers_data,
                mutual_followers=followers_data
            )
        elif cached_profile.parsing_status in ["pending", "processing"]:
            # Проверяем статус задачи
            task_status = "Заглушка <<<<<<" #get_task_status(cached_profile.parse_task_id) if cached_profile.parse_task_id else {"status": "pending"}

            return schemas.FollowersResponse(
                success=True,
                message="Подписчики еще парсятся",
                status=task_status["status"],
                task_id=cached_profile.parse_task_id
            )
        else:
            # Ошибка парсинга
            return schemas.FollowersResponse(
                success=False,
                message="Ошибка при парсинге подписчиков",
                status="failed"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении подписчиков: {str(e)}")

@app.get("/api/profile/{username}/parse-status")
async def get_parse_status(username: str, db: Session = Depends(get_db)):
    """Получить статус парсинга подписчиков"""
    try:
        cached_profile = crud.get_instagram_profile_by_username(db, username.lower())
        
        if not cached_profile:
            raise HTTPException(status_code=404, detail="Профиль не найден")
        
        task_status = {"status": cached_profile.parsing_status}
        if cached_profile.parse_task_id:
            task_status = "Заглушка <<<<<<" #get_task_status(cached_profile.parse_task_id)
        
        return {
            "success": True,
            "status": task_status["status"],
            "task_id": cached_profile.parse_task_id,
            "message": f"Статус парсинга: {task_status['status']}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статуса: {str(e)}")


@app.get("/api/proxy-image")
async def proxy_image(url: str):
    """Прокси для изображений Instagram для обхода CORS"""
    try:
        if not url or not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL")
        
        # Заголовки для имитации браузера
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Получаем изображение
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Возвращаем изображение с правильными заголовками
        return Response(
            content=response.content,
            media_type=response.headers.get('content-type', 'image/jpeg'),
            headers={
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Access-Control-Allow-Headers': 'Content-Type',
            }
        )
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

# ===== TARIFF ENDPOINTS =====

@app.get("/api/tariffs", response_model=List[schemas.Tariff])
async def get_tariffs(db: Session = Depends(get_db)):
    """Получить все активные тарифы"""
    return crud.get_all_tariffs(db, active_only=True)

@app.get("/api/tariffs/{tariff_id}", response_model=schemas.Tariff)
async def get_tariff(tariff_id: int, db: Session = Depends(get_db)):
    """Получить тариф по ID"""
    tariff = crud.get_tariff_by_id(db, tariff_id)
    if not tariff:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    return schemas.Tariff.model_validate(tariff)

# ===== SUBSCRIPTION ENDPOINTS =====

@app.post("/api/subscription/purchase", response_model=schemas.SubscriptionResponse)
async def purchase_subscription(request: schemas.SubscriptionRequest, db: Session = Depends(get_db)):
    """Покупка подписки через CloudPayments с поддержкой рекуррентных платежей"""
    try:
        from payment_service import get_payment_service
        
        # Детальное логирование входящего запроса
        logger.info(f"=== PURCHASE SUBSCRIPTION REQUEST ===")
        logger.info(f"User ID: {request.user_id}")
        logger.info(f"Tariff ID: {request.tariff_id}")
        logger.info(f"Card Token: {getattr(request, 'card_token', None)}")
        logger.info(f"Transaction ID: {getattr(request, 'transaction_id', None)}")
        logger.info(f"Request dict: {request.model_dump()}")
        
        payment_service = get_payment_service(db, test_mode=False)  # Тестовый режим (пока нет боевых credentials)
        
        # Если есть токен карты - создаём рекуррентную подписку
        card_token = getattr(request, 'card_token', None)
        transaction_id = getattr(request, 'transaction_id', None)
        
        if card_token:
            logger.info(f"✅ Card token found: {card_token[:20]}... - Creating recurrent subscription")
            result = payment_service.create_recurrent_subscription(
                user_id=request.user_id,
                tariff_id=request.tariff_id,
                card_token=card_token,
                transaction_id=transaction_id
            )
        else:
            # Обычная активация подписки без автопродления (для старых платежей или тарифов без рекуррента)
            logger.warning(f"⚠️ NO CARD TOKEN - Activating simple subscription without auto-renewal")
            result = payment_service.activate_subscription_simple(
                user_id=request.user_id,
                tariff_id=request.tariff_id,
                transaction_id=transaction_id
            )
        
        if result["success"]:
            return schemas.SubscriptionResponse(
                success=True,
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error purchasing subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при покупке подписки: {str(e)}")

@app.post("/api/subscription/pause")
async def pause_subscription(request: schemas.PauseSubscriptionRequest, db: Session = Depends(get_db)):
    """Приостановка подписки"""
    try:
        subscription = crud.pause_subscription(db, request.user_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Активная подписка не найдена")
        
        return {"success": True, "message": "Подписка приостановлена на 7 дней"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при приостановке подписки: {str(e)}")

@app.post("/api/subscription/cancel")
async def cancel_subscription(request: schemas.CancelSubscriptionRequest, db: Session = Depends(get_db)):
    """Отмена подписки с проверкой данных карты"""
    try:
        from payment_service import get_payment_service
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"📝 Cancel subscription request for user {request.user_id}")
        logger.info(f"   Card: {request.card_first_six}******{request.card_last_four}")
        logger.info(f"   Account ID: {request.account_id}")
        logger.info(f"   Reason: {request.reason}")
        
        # Проверяем, что ID аккаунта совпадает с user_id
        if request.account_id != request.user_id:
            logger.warning(f"❌ Account ID mismatch: {request.account_id} != {request.user_id}")
            raise HTTPException(status_code=400, detail="ID аккаунта не совпадает")
        
        # Получаем активную подписку пользователя
        subscription = db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.user_id == request.user_id,
            models.SubscriptionHistory.status.in_(["active", "paused"])
        ).first()
        
        if not subscription:
            logger.warning(f"❌ No active subscription found for user {request.user_id}")
            raise HTTPException(status_code=404, detail="Активная подписка не найдена")
        
        # Проверяем данные карты (если есть card_token, проверяем последние 4 цифры)
        # Примечание: CloudPayments не возвращает полные данные карты, поэтому проверяем только наличие подписки
        logger.info(f"✅ Subscription found: {subscription.id}, status: {subscription.status}")
        
        # Отменяем подписку через PaymentService
        payment_service = get_payment_service(db, test_mode=False)
        result = payment_service.cancel_subscription(request.user_id)
        
        if result["success"]:
            logger.info(f"✅ Subscription cancelled successfully for user {request.user_id}")
            return {"success": True, "message": "Подписка успешно отменена"}
        else:
            logger.error(f"❌ Failed to cancel subscription: {result['message']}")
            raise HTTPException(status_code=400, detail=result["message"])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelling subscription: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при отмене подписки: {str(e)}")

@app.get("/api/subscription/status/{user_id}")
async def get_subscription_status(user_id: str, db: Session = Depends(get_db)):
    """Получить статус подписки пользователя"""
    try:
        user = crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        active_subscription = crud.get_user_active_subscription(db, user_id)
        
        return {
            "user_id": user_id,
            "has_active_subscription": active_subscription is not None,
            "current_tariff": user.current_tariff.name if user.current_tariff else None,
            "subscription_end": user.subscription_end,
            "remaining_requests": user.remaining_requests
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статуса подписки: {str(e)}")

# ===== SUPPORT ENDPOINTS =====

@app.post("/api/support/contact")
async def contact_support(request: schemas.SupportRequestCreate, db: Session = Depends(get_db)):
    """Обращение в поддержку"""
    try:
        support_request = crud.create_support_request(db, request)
        return {"success": True, "message": "Обращение в поддержку принято", "request_id": support_request.id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при отправке обращения: {str(e)}")

# ===== CLOUDPAYMENTS WEBHOOKS =====

@app.post("/api/payments/cloudpayments/notification")
async def cloudpayments_notification(request: Request, db: Session = Depends(get_db)):
    """Обработка уведомлений от CloudPayments"""
    try:
        from payment_service import get_payment_service
        
        # Получаем сырое тело запроса
        body = await request.body()
        logger.info(f"=" * 70)
        logger.info(f"🔔 CLOUDPAYMENTS WEBHOOK RECEIVED")
        logger.info(f"=" * 70)
        logger.info(f"Raw body: {body}")
        logger.info(f"Body length: {len(body)}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Проверяем формат данных
        if not body:
            logger.warning(f"⚠️ Empty webhook body - ignoring")
            return {"code": 0}
        
        content_type = request.headers.get("content-type", "")
        
        # CloudPayments может отправлять данные в двух форматах:
        # 1. application/json
        # 2. application/x-www-form-urlencoded
        
        if "application/json" in content_type:
            try:
                notification_data = await request.json()
            except Exception as json_error:
                logger.error(f"❌ Failed to parse JSON: {json_error}")
                return {"code": 0}
        elif "application/x-www-form-urlencoded" in content_type:
            # Парсим form data
            from urllib.parse import parse_qs
            body_str = body.decode('utf-8')
            parsed = parse_qs(body_str)
            # parse_qs возвращает списки, берём первое значение
            notification_data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
            logger.info(f"📝 Parsed form data: {notification_data}")
        else:
            logger.error(f"❌ Unknown content type: {content_type}")
            return {"code": 0}
        
        hmac_header = request.headers.get("X-Content-HMAC", "")
        
        # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ
        logger.info(f"Notification data: {notification_data}")
        logger.info(f"Account ID: {notification_data.get('AccountId')}")
        logger.info(f"Transaction ID: {notification_data.get('TransactionId')}")
        logger.info(f"Amount: {notification_data.get('Amount')}")
        logger.info(f"Status: {notification_data.get('Status')}")
        logger.info(f"Token: {notification_data.get('Token', 'NO TOKEN')}")
        logger.info(f"=" * 70)
        
        payment_service = get_payment_service(db, test_mode=True)  # Тестовый режим (пока нет боевых credentials)
        
        # Проверяем подпись (в продакшене обязательно!)
        # if not payment_service.cp_client.verify_notification(notification_data, hmac_header):
        #     raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Обрабатываем уведомление
        result = payment_service.handle_payment_notification(notification_data)
        
        logger.info(f"✅ Webhook processed with code: {result.get('code', 0)}")
        
        return {"code": result.get("code", 0)}
        
    except Exception as e:
        logger.error(f"❌ CloudPayments notification error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"code": 0}  # Возвращаем success, чтобы не было повторных попыток

# ===== SUBSCRIPTION MANAGEMENT ENDPOINTS =====

@app.post("/api/subscription/resume")
async def resume_subscription(request: schemas.PauseSubscriptionRequest, db: Session = Depends(get_db)):
    """Возобновление подписки"""
    try:
        from payment_service import get_payment_service
        
        payment_service = get_payment_service(db, test_mode=True)  # Тестовый режим (пока нет боевых credentials)
        result = payment_service.resume_subscription(request.user_id)
        
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при возобновлении подписки: {str(e)}")

@app.post("/api/subscription/cancel-full")
async def cancel_subscription_full(request: schemas.PauseSubscriptionRequest, db: Session = Depends(get_db)):
    """Полная отмена подписки"""
    try:
        from payment_service import get_payment_service
        
        payment_service = get_payment_service(db, test_mode=True)  # Тестовый режим (пока нет боевых credentials)
        result = payment_service.cancel_subscription(request.user_id)
        
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при отмене подписки: {str(e)}")


# ===== IMAGE STORAGE ENDPOINTS =====

@app.get("/api/storage/stats")
async def get_storage_stats():
    """Получить статистику хранилища изображений"""
    try:
        from image_storage import get_storage_stats
        stats = get_storage_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики: {str(e)}")


@app.post("/api/storage/cleanup")
async def cleanup_old_images(days: int = 30):
    """Удалить старые изображения"""
    try:
        from image_storage import cleanup_old_images
        deleted_count = cleanup_old_images(days)
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Удалено {deleted_count} изображений старше {days} дней"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при очистке: {str(e)}")


@app.get("/api/storage/debug")
async def debug_storage():
    """Debug endpoint для проверки storage"""
    import os
    from pathlib import Path
    
    cwd = os.getcwd()
    storage_path = Path("storage")
    images_path = Path("storage/images")
    posts_path = Path("storage/images/posts")
    
    result = {
        "cwd": str(cwd),
        "storage_exists": storage_path.exists(),
        "storage_absolute": str(storage_path.absolute()),
        "images_exists": images_path.exists(),
        "images_absolute": str(images_path.absolute()),
        "posts_exists": posts_path.exists(),
        "posts_absolute": str(posts_path.absolute()),
    }
    
    # Список файлов в posts
    if posts_path.exists():
        files = list(posts_path.glob("*.jpg"))
        result["posts_files_count"] = len(files)
        result["posts_files_sample"] = [f.name for f in files[:5]]
    
    # Проверяем конкретный файл
    test_file = Path("storage/images/posts/post_C87V_ezogza_9884f233f036a22ad167a56e7f2ec84b.jpg")
    result["test_file"] = {
        "path": str(test_file.absolute()),
        "exists": test_file.exists(),
        "size": test_file.stat().st_size if test_file.exists() else None
    }
    
    return result


# ===== IMAGE SERVING ENDPOINT =====
@app.get("/storage/{file_path:path}")
async def serve_storage_file(file_path: str):
    """Раздача файлов из storage"""
    from pathlib import Path
    from fastapi.responses import FileResponse
    import mimetypes
    
    # Полный путь к файлу
    full_path = Path("storage") / file_path
    
    # Проверяем существование файла
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    # Определяем MIME-тип
    mime_type, _ = mimetypes.guess_type(str(full_path))
    if mime_type is None:
        mime_type = "application/octet-stream"
    
    # Возвращаем файл
    return FileResponse(
        path=str(full_path),
        media_type=mime_type,
        headers={
            "Cache-Control": "public, max-age=86400",  # Кэш на 1 день
            "Access-Control-Allow-Origin": "*",
        }
    )


#if __name__ == "__main__":

#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)
