"""
Админ панель для InstardingBot
Монолитное решение через FastAPI с веб-интерфейсом
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import json
import csv
import io
from datetime import datetime, timedelta

import crud
import models
import schemas
from database import get_db

# Создаем роутер для админки
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# ===== ДАШБОРД =====

@admin_router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Главная страница админки с дашбордом"""
    
    # Получаем все метрики
    metrics = get_metrics_data(db)
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "metrics": metrics,
        "page_title": "Дашборд"
    })

def get_metrics_data(db: Session):
    """Внутренняя функция для получения метрик"""
    
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Основные метрики
    total_users = crud.get_total_users_count(db)
    active_users_today = crud.get_active_users_count(db, today)
    active_users_week = crud.get_active_users_count(db, week_ago)
    new_users_today = crud.get_new_users_count(db, today)
    new_users_week = crud.get_new_users_count(db, week_ago)
    
    # Профили
    total_profiles = crud.get_total_profiles_count(db)
    profiles_today = crud.get_profiles_parsed_count(db, today)
    profiles_week = crud.get_profiles_parsed_count(db, week_ago)
    profiles_in_progress = crud.get_profiles_in_progress_count(db)
    
    # Подписки
    total_subscriptions = crud.get_total_subscriptions_count(db)
    subscriptions_today = crud.get_subscriptions_count(db, today)
    subscriptions_week = crud.get_subscriptions_count(db, week_ago)
    active_subscriptions = crud.get_active_subscriptions_count(db)
    
    # Доходы
    revenue_today = crud.get_revenue(db, today)
    revenue_week = crud.get_revenue(db, week_ago)
    revenue_month = crud.get_revenue(db, month_ago)
    
    # Статистика по тарифам
    tariff_stats = crud.get_tariff_statistics(db)
    
    # Парсинг статистика
    parsing_stats = crud.get_parsing_statistics(db)
    
    return {
        "users": {
            "total": total_users,
            "active_today": active_users_today,
            "active_week": active_users_week,
            "new_today": new_users_today,
            "new_week": new_users_week,
            "growth_rate": round((new_users_today / max(total_users - new_users_today, 1)) * 100, 2)
        },
        "profiles": {
            "total": total_profiles,
            "parsed_today": profiles_today,
            "parsed_week": profiles_week,
            "in_progress": profiles_in_progress,
            "completion_rate": round((total_profiles - profiles_in_progress) / max(total_profiles, 1) * 100, 2)
        },
        "subscriptions": {
            "total": total_subscriptions,
            "today": subscriptions_today,
            "week": subscriptions_week,
            "active": active_subscriptions,
            "conversion_rate": round((total_subscriptions / max(total_users, 1)) * 100, 2)
        },
        "revenue": {
            "today": revenue_today,
            "week": revenue_week,
            "month": revenue_month,
            "avg_per_user": round(revenue_month / max(total_users, 1), 2)
        },
        "tariffs": tariff_stats,
        "parsing": parsing_stats
    }

@admin_router.get("/api/metrics")
async def api_get_dashboard_metrics(db: Session = Depends(get_db)):
    """API endpoint для получения метрик дашборда"""
    return get_metrics_data(db)

# ===== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ =====

@admin_router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db), 
                     page: int = 1, search: Optional[str] = None,
                     page_size: int = 50, sort: Optional[str] = None):
    """Страница управления пользователями"""
    
    # Ограничиваем размер страницы
    page_size = min(max(page_size, 10), 1000)
    
    users = crud.get_users_with_stats(db, page=page, search=search, page_size=page_size, sort=sort)
    total_users = crud.get_total_users_count(db)
    total_pages = (total_users + page_size - 1) // page_size  # Округление вверх
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "users": users,
        "current_page": page,
        "total_pages": total_pages,
        "search": search or "",
        "page_size": page_size,
        "sort": sort or "created_desc",
        "page_title": "Управление пользователями"
    })

@admin_router.post("/users/{user_id}/delete")
async def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Удаление пользователя"""
    try:
        success = crud.delete_user_completely(db, user_id)
        if success:
            return {"success": True, "message": "Пользователь удален"}
        else:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.get("/users/{user_id}/details")
async def get_user_details(user_id: str, db: Session = Depends(get_db)):
    """Получить детальную информацию о пользователе"""
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return {
        "user_id": user.user_id,
        "is_active": user.is_active,
        "is_paid": user.is_paid,
        "current_tariff_id": user.current_tariff_id,
        "remaining_requests": user.remaining_requests,
        "subscription_start": user.subscription_start.isoformat() if user.subscription_start else None,
        "subscription_end": user.subscription_end.isoformat() if user.subscription_end else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "total_requests": user.total_requests
    }

@admin_router.post("/users/{user_id}/edit")
async def edit_user(user_id: str, user_data: dict, db: Session = Depends(get_db)):
    """Редактирование пользователя"""
    try:
        success = crud.update_user_details(db, user_id, user_data)
        if success:
            return {"success": True, "message": "Данные пользователя обновлены"}
        else:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/users/{user_id}/tariff")
async def update_user_tariff(user_id: str, tariff_id: int = Form(...), db: Session = Depends(get_db)):
    """Изменение тарифа пользователя"""
    try:
        success = crud.update_user_tariff(db, user_id, tariff_id)
        if success:
            return {"success": True, "message": "Тариф обновлен"}
        else:
            raise HTTPException(status_code=404, detail="Пользователь или тариф не найден")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== УПРАВЛЕНИЕ ЗАПРОСАМИ/ПРОФИЛЯМИ =====

@admin_router.get("/profiles", response_class=HTMLResponse)
async def admin_profiles(request: Request, db: Session = Depends(get_db),
                        page: int = 1, search: Optional[str] = None, 
                        status: Optional[str] = None, page_size: int = 30,
                        sort: Optional[str] = None):
    """Страница всех спаршенных профилей"""
    
    # Ограничиваем размер страницы
    page_size = min(max(page_size, 10), 500)
    
    profiles = crud.get_profiles_with_details(db, page=page, search=search, 
                                            status=status, page_size=page_size, sort=sort)
    total_profiles = crud.get_total_profiles_count(db)
    total_pages = (total_profiles + page_size - 1) // page_size
    
    return templates.TemplateResponse("admin/profiles.html", {
        "request": request,
        "profiles": profiles,
        "current_page": page,
        "total_pages": total_pages,
        "search": search or "",
        "status": status or "",
        "page_size": page_size,
        "sort": sort or "created_desc",
        "page_title": "Все запросы"
    })

@admin_router.get("/profiles/{profile_id}/details")
async def get_profile_details(profile_id: int, db: Session = Depends(get_db)):
    """Получить детальную информацию о профиле для поп-апа"""
    
    profile = crud.get_profile_full_details(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    
    return {
        "profile": profile,
        "followers_count": crud.get_profile_followers_count(db, profile_id),
        "mutual_followers": crud.get_profile_mutual_followers(db, profile_id),
        "parsing_history": crud.get_profile_parsing_history(db, profile_id)
    }

# ===== СТАТИСТИКА ПО ПОДПИСКАМ =====

@admin_router.get("/subscriptions", response_class=HTMLResponse)
async def admin_subscriptions(request: Request, db: Session = Depends(get_db)):
    """Страница статистики по подпискам"""
    
    subscription_stats = crud.get_detailed_subscription_statistics(db)
    tariff_stats = crud.get_tariff_performance_stats(db)
    revenue_stats = crud.get_revenue_by_tariff(db)
    
    return templates.TemplateResponse("admin/subscriptions.html", {
        "request": request,
        "subscription_stats": subscription_stats,
        "tariff_stats": tariff_stats,
        "revenue_stats": revenue_stats,
        "page_title": "Статистика подписок"
    })

# ===== API ДЛЯ AJAX ЗАПРОСОВ =====

@admin_router.get("/api/users/search")
async def search_users(q: str, db: Session = Depends(get_db)):
    """Поиск пользователей для автокомплита"""
    users = crud.search_users(db, q, limit=10)
    return [{"id": u.user_id, "text": f"{u.user_id} ({u.total_requests} запросов)"} for u in users]

@admin_router.get("/api/profiles/search")
async def search_profiles(q: str, db: Session = Depends(get_db)):
    """Поиск профилей для автокомплита"""
    profiles = crud.search_profiles(db, q, limit=10)
    return [{"id": p.id, "text": f"@{p.username} ({p.followers_count} подписчиков)"} for p in profiles]

@admin_router.post("/api/profiles/{profile_id}/reparse")
async def reparse_profile(profile_id: int, db: Session = Depends(get_db)):
    """Повторный парсинг профиля"""
    try:
        success = crud.trigger_profile_reparse(db, profile_id)
        if success:
            return {"success": True, "message": "Парсинг запущен"}
        else:
            raise HTTPException(status_code=404, detail="Профиль не найден")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== ЭКСПОРТ В CSV =====

@admin_router.get("/users/export")
async def export_users_csv(db: Session = Depends(get_db), search: Optional[str] = None):
    """Экспорт пользователей в CSV"""
    
    # Получаем всех пользователей с фильтром
    users = crud.get_users_with_stats(db, page=1, search=search, page_size=10000)
    
    # Создаем CSV в памяти
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        'User ID', 'Дата регистрации', 'Последний вход', 'Активен', 
        'Имеет подписку', 'Тариф', 'Дата окончания подписки',
        'Всего запросов', 'Оставшиеся запросы'
    ])
    
    # Данные
    for user_data in users:
        user = user_data['user']
        writer.writerow([
            user.user_id,
            user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '',
            user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '',
            'Да' if user.is_active else 'Нет',
            'Да' if user_data['has_active_subscription'] else 'Нет',
            user_data['tariff_name'],
            user.subscription_end.strftime('%Y-%m-%d') if user.subscription_end else '',
            user_data['profiles_count'],
            user.remaining_requests or 0
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@admin_router.get("/profiles/export")
async def export_profiles_csv(db: Session = Depends(get_db), 
                            search: Optional[str] = None, 
                            status: Optional[str] = None):
    """Экспорт профилей в CSV"""
    
    # Получаем все профили с фильтрами
    profiles = crud.get_profiles_with_details(db, page=1, search=search, status=status, page_size=10000)
    
    # Создаем CSV в памяти
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        'Username', 'Полное имя', 'Подписчики', 'Подписки', 'Посты',
        'Статус парсинга', 'Сохранено подписчиков', 'Успешность (%)',
        'Дата создания', 'Последнее обновление', 'Верифицирован', 'Приватный'
    ])
    
    # Данные
    for profile_data in profiles:
        profile = profile_data['profile']
        writer.writerow([
            profile.username,
            profile.full_name or '',
            profile.followers_count or 0,
            profile.following_count or 0,
            profile.posts_count or 0,
            profile.parsing_status,
            profile_data['followers_saved'],
            f"{profile_data['success_rate']:.1f}",
            profile.created_at.strftime('%Y-%m-%d %H:%M:%S') if profile.created_at else '',
            profile.last_scraped.strftime('%Y-%m-%d %H:%M:%S') if profile.last_scraped else '',
            'Да' if profile.is_verified else 'Нет',
            'Да' if profile.is_private else 'Нет'
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=profiles_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

# ===== TELEGRAM РАССЫЛКИ =====

@admin_router.get("/broadcasts", response_class=HTMLResponse)
async def admin_broadcasts(request: Request, db: Session = Depends(get_db)):
    """Страница управления рассылками"""
    
    # Получаем статистику пользователей
    total_users = crud.get_total_users_count(db)
    paid_users = crud.get_active_subscriptions_count(db)
    free_users = total_users - paid_users
    
    user_stats = {
        "total_users": total_users,
        "paid_users": paid_users,
        "free_users": free_users
    }
    
    # Статистика рассылок (заглушка, можно расширить)
    broadcast_stats = {
        "total_sent": 0,
        "today_sent": 0,
        "success_rate": 95.5
    }
    
    return templates.TemplateResponse("admin/broadcasts.html", {
        "request": request,
        "user_stats": user_stats,
        "broadcast_stats": broadcast_stats,
        "page_title": "Telegram рассылки"
    })

@admin_router.post("/broadcasts/send")
async def send_broadcast(broadcast_data: dict, db: Session = Depends(get_db)):
    """Отправка рассылки"""
    try:
        from telegram_sender import get_broadcast_manager
        
        manager = get_broadcast_manager()
        if not manager:
            raise HTTPException(status_code=500, detail="Telegram рассылки не настроены")
        
        result = await manager.create_broadcast(db, broadcast_data)
        
        if result['success']:
            return {"success": True, "results": result['results']}
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.get("/api/users/list")
async def get_users_list(db: Session = Depends(get_db)):
    """Получить список пользователей для рассылки"""
    users = crud.get_users_for_broadcast(db, limit=1000)
    
    return users

# ===== API ДЛЯ ВИРТУАЛЬНОГО СКРОЛЛА =====

@admin_router.get("/api/users/virtual")
async def get_users_virtual(db: Session = Depends(get_db), 
                          offset: int = 0, limit: int = 100,
                          search: Optional[str] = None, sort: Optional[str] = None):
    """API для виртуального скролла пользователей"""
    
    # Ограничиваем лимит
    limit = min(max(limit, 10), 1000)
    
    users = crud.get_users_virtual_scroll(db, offset=offset, limit=limit, search=search, sort=sort)
    total_count = crud.get_total_users_count(db)
    
    return {
        "data": [
            {
                "user_id": user_data['user'].user_id,
                "display_name": user_data['display_name'],
                "ig_username": user_data['ig_username'],
                "ig_full_name": user_data['ig_full_name'],
                "created_at": user_data['user'].created_at.isoformat() if user_data['user'].created_at else '',
                "last_login": user_data['user'].last_login.isoformat() if user_data['user'].last_login else '',
                "is_active": user_data['user'].is_active,
                "profiles_count": user_data['profiles_count'],
                "tariff_name": user_data['tariff_name'],
                "has_subscription": user_data['has_active_subscription'],
                "subscription_end": user_data['user'].subscription_end.isoformat() if user_data['user'].subscription_end else '',
                "remaining_requests": user_data['user'].remaining_requests or 0
            }
            for user_data in users
        ],
        "total": total_count,
        "offset": offset,
        "limit": limit
    }

@admin_router.get("/api/profiles/virtual")
async def get_profiles_virtual(db: Session = Depends(get_db),
                             offset: int = 0, limit: int = 100,
                             search: Optional[str] = None, status: Optional[str] = None,
                             sort: Optional[str] = None):
    """API для виртуального скролла профилей"""
    
    # Ограничиваем лимит
    limit = min(max(limit, 10), 1000)
    
    profiles = crud.get_profiles_virtual_scroll(db, offset=offset, limit=limit, 
                                              search=search, status=status, sort=sort)
    total_count = crud.get_total_profiles_count(db)
    
    return {
        "data": [
            {
                "id": profile_data['profile']['id'],
                "username": profile_data['profile']['username'],
                "full_name": profile_data['profile']['full_name'] or '',
                "followers_count": profile_data['profile']['followers_count'] or 0,
                "following_count": profile_data['profile']['following_count'] or 0,
                "posts_count": profile_data['profile']['posts_count'] or 0,
                "parsing_status": profile_data['profile']['parsing_status'],
                "followers_saved": profile_data['followers_saved'],
                "success_rate": profile_data['success_rate'],
                "created_at": profile_data['profile']['created_at'].isoformat() if profile_data['profile']['created_at'] else '',
                "last_scraped": profile_data['profile']['last_scraped'].isoformat() if profile_data['profile']['last_scraped'] else '',
                "is_verified": profile_data['profile']['is_verified'],
                "is_private": profile_data['profile']['is_private'],
                "profile_pic_url": profile_data['profile']['profile_pic_url'] or ''
            }
            for profile_data in profiles
        ],
        "total": total_count,
        "offset": offset,
        "limit": limit
    }

# ===== ОТЛАДОЧНЫЕ ENDPOINTS =====

@admin_router.get("/debug/profiles/avatars")
async def debug_profile_avatars(db: Session = Depends(get_db)):
    """Отладочный endpoint для проверки аватарок профилей"""
    profiles = db.query(models.InstagramProfile).limit(10).all()
    
    result = []
    for profile in profiles:
        result.append({
            "id": profile.id,
            "username": profile.username,
            "profile_pic_url": profile.profile_pic_url,
            "has_avatar": bool(profile.profile_pic_url),
            "avatar_length": len(profile.profile_pic_url) if profile.profile_pic_url else 0,
            "avatar_preview": profile.profile_pic_url[:100] + "..." if profile.profile_pic_url and len(profile.profile_pic_url) > 100 else profile.profile_pic_url
        })
    
    return {"profiles": result, "total_checked": len(result)}


@admin_router.get("/debug/users/broadcast")
async def debug_users_broadcast(db: Session = Depends(get_db)):
    """Отладочный endpoint для проверки данных пользователей в рассылке"""
    users = crud.get_users_for_broadcast(db, limit=10)
    
    return {
        "users_sample": users,
        "total_users": len(users),
        "users_with_ig_data": len([u for u in users if u['ig_username']]),
        "users_with_display_name": len([u for u in users if u['display_name'] != u['user_id']])
    }


@admin_router.post("/debug/users/create-test-telegram")
async def create_test_telegram_users_endpoint(db: Session = Depends(get_db)):
    """Создать тестовых пользователей с Telegram данными"""
    success = crud.create_test_telegram_users(db)
    
    if success:
        return {"success": True, "message": "Тестовые пользователи созданы/обновлены"}
    else:
        raise HTTPException(status_code=500, detail="Ошибка создания тестовых пользователей")


@admin_router.post("/users/{user_id}/telegram")
async def update_user_telegram_data_endpoint(
    user_id: str, 
    first_name: str = Form(None),
    last_name: str = Form(None), 
    telegram_username: str = Form(None),
    db: Session = Depends(get_db)
):
    """Обновить Telegram данные пользователя"""
    success = crud.update_user_telegram_data(
        db, user_id, first_name, last_name, telegram_username
    )
    
    if success:
        return {"success": True, "message": "Telegram данные обновлены"}
    else:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

# ===== CLOUDPAYMENTS SUBSCRIPTION MANAGEMENT =====

@admin_router.get("/subscriptions/cloudpayments", response_class=HTMLResponse)
async def admin_cloudpayments_subscriptions(request: Request, db: Session = Depends(get_db)):
    """Страница управления CloudPayments подписками"""
    
    # Получаем активные подписки с CloudPayments данными
    active_subscriptions = db.query(models.SubscriptionHistory).filter(
        models.SubscriptionHistory.auto_renewal == True
    ).join(models.User).join(models.Tariff).all()
    
    return templates.TemplateResponse("admin/cloudpayments_subscriptions.html", {
        "request": request,
        "active_subscriptions": active_subscriptions,
        "page_title": "Управление подписками CloudPayments"
    })

@admin_router.post("/subscriptions/{subscription_id}/pause")
async def admin_pause_subscription(subscription_id: int, db: Session = Depends(get_db)):
    """Приостановка подписки через админку"""
    try:
        from payment_service import get_payment_service
        
        subscription = db.query(models.SubscriptionHistory).get(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Подписка не найдена")
        
        payment_service = get_payment_service(db, test_mode=True)
        result = payment_service.pause_subscription(subscription.user_id)
        
        return {"success": result["success"], "message": result["message"]}
        
    except Exception as e:
        return {"success": False, "message": str(e)}

@admin_router.post("/subscriptions/{subscription_id}/resume")
async def admin_resume_subscription(subscription_id: int, db: Session = Depends(get_db)):
    """Возобновление подписки через админку"""
    try:
        from payment_service import get_payment_service
        
        subscription = db.query(models.SubscriptionHistory).get(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Подписка не найдена")
        
        payment_service = get_payment_service(db, test_mode=True)
        result = payment_service.resume_subscription(subscription.user_id)
        
        return {"success": result["success"], "message": result["message"]}
        
    except Exception as e:
        return {"success": False, "message": str(e)}

@admin_router.post("/subscriptions/{subscription_id}/cancel")
async def admin_cancel_subscription(subscription_id: int, db: Session = Depends(get_db)):
    """Полная отмена подписки через админку"""
    try:
        from payment_service import get_payment_service
        
        subscription = db.query(models.SubscriptionHistory).get(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Подписка не найдена")
        
        payment_service = get_payment_service(db, test_mode=True)
        result = payment_service.cancel_subscription(subscription.user_id)
        
        return {"success": result["success"], "message": result["message"]}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


# ===== PARSER CONFIGURATION =====

@admin_router.get("/parser-config", response_class=HTMLResponse)
async def admin_parser_config(request: Request):
    """Страница управления конфигурацией парсера"""
    from parser_config import get_parser_config
    
    config = get_parser_config()
    all_config = config.get_all_config()
    
    return templates.TemplateResponse("admin/parser_config.html", {
        "request": request,
        "cookies": all_config.get("cookies", []),
        "timings": all_config.get("timings", {}),
        "page_title": "Настройки парсера"
    })

@admin_router.get("/api/parser-config")
async def get_parser_config_api():
    """API: Получить конфигурацию парсера"""
    from parser_config import get_parser_config
    
    config = get_parser_config()
    return {
        "success": True,
        "config": config.get_all_config()
    }

@admin_router.post("/api/parser-config/cookies/add")
async def add_cookie(cookie_data: dict):
    """API: Добавить новый cookie"""
    from parser_config import get_parser_config
    
    cookie = cookie_data.get("cookie", "").strip()
    if not cookie:
        raise HTTPException(status_code=400, detail="Cookie не может быть пустым")
    
    config = get_parser_config()
    if config.add_cookie(cookie):
        return {"success": True, "message": "Cookie добавлен"}
    else:
        return {"success": False, "message": "Cookie уже существует"}

@admin_router.post("/api/parser-config/cookies/{index}/update")
async def update_cookie(index: int, cookie_data: dict):
    """API: Обновить cookie по индексу"""
    from parser_config import get_parser_config
    
    cookie = cookie_data.get("cookie", "").strip()
    if not cookie:
        raise HTTPException(status_code=400, detail="Cookie не может быть пустым")
    
    config = get_parser_config()
    if config.update_cookie(index, cookie):
        return {"success": True, "message": "Cookie обновлён"}
    else:
        raise HTTPException(status_code=400, detail="Неверный индекс")

@admin_router.delete("/api/parser-config/cookies/{index}")
async def delete_cookie(index: int):
    """API: Удалить cookie по индексу"""
    from parser_config import get_parser_config
    
    config = get_parser_config()
    cookies = config.get_cookies()
    
    if len(cookies) <= 1:
        raise HTTPException(status_code=400, detail="Нельзя удалить последний cookie")
    
    if config.remove_cookie(index):
        return {"success": True, "message": "Cookie удалён"}
    else:
        raise HTTPException(status_code=400, detail="Неверный индекс")

@admin_router.post("/api/parser-config/timings")
async def update_timings(timings_data: dict):
    """API: Обновить настройки таймингов"""
    from parser_config import get_parser_config
    
    try:
        # Валидация данных
        timings = timings_data.get("timings", {})
        
        # Конвертируем в нужные типы
        validated_timings = {}
        
        float_fields = ["base_delay", "jitter_min", "jitter_max", "additional_delay_min", "additional_delay_max"]
        int_fields = ["timeout", "max_retries", "page_size", "max_followers", "max_followings"]
        
        for field in float_fields:
            if field in timings:
                validated_timings[field] = float(timings[field])
        
        for field in int_fields:
            if field in timings:
                validated_timings[field] = int(timings[field])
        
        config = get_parser_config()
        if config.update_timings(validated_timings):
            return {"success": True, "message": "Настройки таймингов обновлены"}
        else:
            raise HTTPException(status_code=500, detail="Ошибка обновления таймингов")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат данных: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/api/parser-config/reset")
async def reset_config():
    """API: Сброс конфигурации на значения по умолчанию"""
    from parser_config import get_parser_config
    
    config = get_parser_config()
    if config.reset_to_defaults():
        return {"success": True, "message": "Конфигурация сброшена на значения по умолчанию"}
    else:
        raise HTTPException(status_code=500, detail="Ошибка сброса конфигурации")
