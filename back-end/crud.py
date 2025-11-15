from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import models
import schemas


# ===== USER CRUD =====

def get_user_by_id(db: Session, user_id: str) -> Optional[models.User]:
    """Получить пользователя по ID"""
    return db.query(models.User).filter(models.User.user_id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Создать нового пользователя"""
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: str, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Обновить данные пользователя"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_last_login(db: Session, user_id: str) -> Optional[models.User]:
    """Обновить время последнего входа пользователя"""
    db_user = get_user_by_id(db, user_id)
    if db_user:
        db_user.last_login = datetime.now()
        db.commit()
        db.refresh(db_user)
    return db_user


def increment_user_requests(db: Session, user_id: str) -> Optional[models.User]:
    """Увеличить счетчик запросов пользователя"""
    db_user = get_user_by_id(db, user_id)
    if db_user:
        db_user.total_requests += 1
        # Уменьшаем remaining_requests только если он не None и больше 0
        if db_user.remaining_requests is not None and db_user.remaining_requests > 0:
            db_user.remaining_requests -= 1
        db.commit()
        db.refresh(db_user)
    return db_user


def is_first_profile_parse(db: Session, user_id: str) -> bool:
    """Проверить, первый ли это парсинг профиля для пользователя"""
    activity_count = db.query(models.UserActivity).filter(
        models.UserActivity.user_id == user_id,
        models.UserActivity.activity_type == "profile_parse"
    ).count()
    
    return activity_count == 0


# ===== TARIFF CRUD =====

def get_all_tariffs(db: Session, active_only: bool = True) -> List[models.Tariff]:
    """Получить все тарифы"""
    query = db.query(models.Tariff)
    if active_only:
        query = query.filter(models.Tariff.is_active == True)
    return query.order_by(models.Tariff.price).all()


def get_tariff_by_id(db: Session, tariff_id: int) -> Optional[models.Tariff]:
    """Получить тариф по ID"""
    return db.query(models.Tariff).filter(models.Tariff.id == tariff_id).first()


def get_tariff_by_name(db: Session, name: str) -> Optional[models.Tariff]:
    """Получить тариф по названию"""
    return db.query(models.Tariff).filter(models.Tariff.name == name).first()

def create_payment(db: Session, payment_data: dict) -> models.Payment:
    """Создать запись о платеже"""
    payment = models.Payment(**payment_data)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

def update_payment(db: Session, payment_id: int, update_data: dict) -> models.Payment:
    """Обновить платеж"""
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if payment:
        for key, value in update_data.items():
            setattr(payment, key, value)
        db.commit()
        db.refresh(payment)
    return payment

def get_payment_by_transaction_id(db: Session, transaction_id: str) -> Optional[models.Payment]:
    """Получить платеж по ID транзакции CloudPayments"""
    return db.query(models.Payment).filter(
        models.Payment.cloudpayments_transaction_id == transaction_id
    ).first()

def get_active_subscription_by_user(db: Session, user_id: str) -> Optional[models.SubscriptionHistory]:
    """Получить активную подписку пользователя с автопродлением"""
    return db.query(models.SubscriptionHistory).filter(
        models.SubscriptionHistory.user_id == user_id,
        models.SubscriptionHistory.status.in_(["active", "paused"]),
        models.SubscriptionHistory.auto_renewal == True
    ).first()


def create_tariff(db: Session, tariff: schemas.TariffCreate) -> models.Tariff:
    """Создать новый тариф"""
    db_tariff = models.Tariff(**tariff.dict())
    db.add(db_tariff)
    db.commit()
    db.refresh(db_tariff)
    return db_tariff


def update_tariff(db: Session, tariff_id: int, tariff_update: schemas.TariffUpdate) -> Optional[models.Tariff]:
    """Обновить тариф"""
    db_tariff = get_tariff_by_id(db, tariff_id)
    if not db_tariff:
        return None
    
    update_data = tariff_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tariff, field, value)
    
    db.commit()
    db.refresh(db_tariff)
    return db_tariff


# ===== INSTAGRAM PROFILE CRUD =====

def get_instagram_profile_by_username(db: Session, username: str) -> Optional[models.InstagramProfile]:
    """Получить Instagram профиль по username"""
    return db.query(models.InstagramProfile).filter(models.InstagramProfile.username == username).first()


def create_instagram_profile(db: Session, profile: schemas.InstagramProfileCreate) -> models.InstagramProfile:
    """Создать новый Instagram профиль"""
    db_profile = models.InstagramProfile(**profile.dict())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def update_instagram_profile(db: Session, username: str, profile_update: schemas.InstagramProfileUpdate) -> Optional[models.InstagramProfile]:
    """Обновить Instagram профиль"""
    db_profile = get_instagram_profile_by_username(db, username)
    if not db_profile:
        return None
    
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_profile, field, value)
    
    # Обновляем метаданные
    db_profile.last_scraped = datetime.now()
    db_profile.scrape_count += 1
    db_profile.is_data_fresh = True
    
    db.commit()
    db.refresh(db_profile)
    return db_profile


def update_profile_parsing_status(db: Session, username: str, status: str, task_id: str = None) -> Optional[models.InstagramProfile]:
    """Обновить статус парсинга профиля"""
    db_profile = get_instagram_profile_by_username(db, username)
    if not db_profile:
        return None
    
    db_profile.parsing_status = status
    if task_id:
        db_profile.parse_task_id = task_id
    
    if status == "completed":
        db_profile.followers_parsed_at = datetime.now()
        db_profile.followings_parsed_at = datetime.now()
    
    db.commit()
    db.refresh(db_profile)
    return db_profile


def get_mutual_followers(db: Session, profile_id: int) -> List[models.InstagramFollower]:
    """Получить взаимных подписчиков (есть и в подписчиках и в подписках)"""
    # Здесь будет логика для получения взаимных подписчиков
    # Пока возвращаем обычных подписчиков
    return get_instagram_followers(db, profile_id, limit=50)


def is_profile_data_fresh(db_profile: models.InstagramProfile, max_age_hours: int = 24) -> bool:
    """Проверить, актуальны ли данные профиля"""
    if not db_profile or not db_profile.last_scraped:
        return False
    
    try:
        age = datetime.now() - db_profile.last_scraped
        return age < timedelta(hours=max_age_hours)
    except (TypeError, AttributeError) as e:
        print(f"⚠️ Ошибка при проверке свежести профиля: {e}")
        return False


def mark_profile_as_stale(db: Session, username: str) -> Optional[models.InstagramProfile]:
    """Пометить данные профиля как устаревшие"""
    db_profile = get_instagram_profile_by_username(db, username)
    if db_profile:
        db_profile.is_data_fresh = False
        db.commit()
        db.refresh(db_profile)
    return db_profile


# ===== PAYMENT CRUD =====

def create_payment(db: Session, payment: schemas.PaymentCreate) -> models.Payment:
    """Создать новый платеж"""
    db_payment = models.Payment(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


def get_payment_by_id(db: Session, payment_id: int) -> Optional[models.Payment]:
    """Получить платеж по ID"""
    return db.query(models.Payment).filter(models.Payment.id == payment_id).first()


def get_user_payments(db: Session, user_id: str) -> List[models.Payment]:
    """Получить все платежи пользователя"""
    return db.query(models.Payment).filter(models.Payment.user_id == user_id).order_by(models.Payment.created_at.desc()).all()


def update_payment_status(db: Session, payment_id: int, status: str, transaction_id: Optional[str] = None) -> Optional[models.Payment]:
    """Обновить статус платежа"""
    db_payment = get_payment_by_id(db, payment_id)
    if not db_payment:
        return None
    
    db_payment.status = status
    if transaction_id:
        db_payment.transaction_id = transaction_id
    if status == "completed":
        db_payment.paid_at = datetime.now()
    
    db.commit()
    db.refresh(db_payment)
    return db_payment


# ===== SUBSCRIPTION HISTORY CRUD =====

def create_subscription_history(db: Session, subscription: schemas.SubscriptionHistoryCreate) -> models.SubscriptionHistory:
    """Создать запись в истории подписок"""
    db_subscription = models.SubscriptionHistory(**subscription.dict())
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription


def get_user_active_subscription(db: Session, user_id: str) -> Optional[models.SubscriptionHistory]:
    """Получить активную подписку пользователя"""
    try:
        return db.query(models.SubscriptionHistory).filter(
            models.SubscriptionHistory.user_id == user_id,
            models.SubscriptionHistory.status == "active"
        ).first()
    except Exception as e:
        print(f"❌ Ошибка при получении активной подписки для пользователя {user_id}: {e}")
        return None

def has_active_subscription(db: Session, user_id: str) -> bool:
    """Проверить, есть ли у пользователя активная подписка"""
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            return False
        
        # Проверяем is_paid флаг
        if not user.is_paid:
            return False
            
        # Если есть подписка с датой окончания, проверяем её
        if user.subscription_end:
            from datetime import datetime
            if datetime.now() > user.subscription_end:
                # Подписка истекла, обновляем статус
                user.is_paid = False
                user.current_tariff_id = None
                db.commit()
                return False
        
        # Если есть комбо тариф, проверяем оставшиеся запросы
        if user.current_tariff and user.current_tariff.requests_count:
            if user.remaining_requests is not None and user.remaining_requests <= 0:
                # Запросы закончились
                user.is_paid = False
                user.current_tariff_id = None
                db.commit()
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке подписки пользователя {user_id}: {e}")
        return False


def get_user_subscription_history(db: Session, user_id: str) -> List[models.SubscriptionHistory]:
    """Получить историю подписок пользователя"""
    return db.query(models.SubscriptionHistory).filter(
        models.SubscriptionHistory.user_id == user_id
    ).order_by(models.SubscriptionHistory.created_at.desc()).all()


def update_subscription_status(db: Session, subscription_id: int, status: str) -> Optional[models.SubscriptionHistory]:
    """Обновить статус подписки"""
    db_subscription = db.query(models.SubscriptionHistory).filter(models.SubscriptionHistory.id == subscription_id).first()
    if not db_subscription:
        return None
    
    db_subscription.status = status
    if status in ["cancelled", "expired"]:
        db_subscription.end_date = datetime.now()
    
    db.commit()
    db.refresh(db_subscription)
    return db_subscription


def pause_subscription(db: Session, user_id: str, pause_days: int = 7) -> Optional[models.SubscriptionHistory]:
    """Приостановить подписку пользователя"""
    # Сначала ищем активную подписку в истории
    active_subscription = get_user_active_subscription(db, user_id)
    
    if not active_subscription:
        # Если нет записи в истории, но у пользователя есть активная подписка
        # создаем запись в истории и приостанавливаем её
        user = get_user_by_id(db, user_id)
        if user and user.is_paid and user.current_tariff_id:
            from datetime import datetime, timedelta
            
            # Создаем запись в истории подписок
            start_date = user.subscription_start or datetime.now()
            end_date = user.subscription_end
            
            subscription_create = models.SubscriptionHistory(
                user_id=user_id,
                tariff_id=user.current_tariff_id,
                start_date=start_date,
                end_date=end_date,
                status="paused",
                pause_days_used=pause_days
            )
            
            db.add(subscription_create)
            db.commit()
            db.refresh(subscription_create)
            return subscription_create
        else:
            return None
    
    # Если есть активная подписка в истории, приостанавливаем её
    active_subscription.status = "paused"
    active_subscription.pause_days_used += pause_days
    
    db.commit()
    db.refresh(active_subscription)
    return active_subscription


# ===== SUPPORT REQUEST CRUD =====

def create_support_request(db: Session, support_request: schemas.SupportRequestCreate) -> models.SupportRequest:
    """Создать обращение в поддержку"""
    db_request = models.SupportRequest(**support_request.dict())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


def get_support_requests(db: Session, status: Optional[str] = None) -> List[models.SupportRequest]:
    """Получить обращения в поддержку"""
    query = db.query(models.SupportRequest)
    if status:
        query = query.filter(models.SupportRequest.status == status)
    return query.order_by(models.SupportRequest.created_at.desc()).all()


def update_support_request_status(db: Session, request_id: int, status: str) -> Optional[models.SupportRequest]:
    """Обновить статус обращения в поддержку"""
    db_request = db.query(models.SupportRequest).filter(models.SupportRequest.id == request_id).first()
    if not db_request:
        return None
    
    db_request.status = status
    if status == "closed":
        db_request.resolved_at = datetime.now()
    
    db.commit()
    db.refresh(db_request)
    return db_request


# ===== INSTAGRAM FOLLOWERS CRUD =====

def save_instagram_followers(db: Session, profile_id: int, followers_data: List[Dict[str, Any]]) -> List[models.InstagramFollower]:
    """Сохранить подписчиков Instagram профиля"""
    saved_followers = []
    
    for follower_data in followers_data:
        # Проверяем, есть ли уже такой подписчик
        existing_follower = db.query(models.InstagramFollower).filter(
            models.InstagramFollower.profile_id == profile_id,
            models.InstagramFollower.follower_pk == follower_data["follower_pk"]
        ).first()
        
        if existing_follower:
            # Обновляем существующего
            for field, value in follower_data.items():
                if hasattr(existing_follower, field):
                    # Преобразуем булевы поля для безопасности
                    if field in ['is_verified', 'is_private', 'has_anonymous_profile_picture', 'third_party_downloads_enabled']:
                        value = bool(value) if value is not None else False
                    setattr(existing_follower, field, value)
            existing_follower.updated_at = datetime.now()
            saved_followers.append(existing_follower)
        else:
            # Создаем нового
            # Преобразуем булевы поля для безопасности
            clean_data = follower_data.copy()
            for field in ['is_verified', 'is_private', 'has_anonymous_profile_picture', 'third_party_downloads_enabled']:
                if field in clean_data:
                    clean_data[field] = bool(clean_data[field]) if clean_data[field] is not None else False
            
            db_follower = models.InstagramFollower(
                profile_id=profile_id,
                **clean_data
            )
            db.add(db_follower)
            saved_followers.append(db_follower)
    
    db.commit()
    for follower in saved_followers:
        db.refresh(follower)
    
    return saved_followers


def get_instagram_followers(db: Session, profile_id: int, limit: Optional[int] = None) -> List[models.InstagramFollower]:
    """Получить подписчиков Instagram профиля"""
    query = db.query(models.InstagramFollower).filter(models.InstagramFollower.profile_id == profile_id).order_by(models.InstagramFollower.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_followers_count(db: Session, profile_id: int) -> int:
    """Получить количество сохраненных подписчиков"""
    return db.query(models.InstagramFollower).filter(models.InstagramFollower.profile_id == profile_id).count()


def delete_old_followers(db: Session, profile_id: int, keep_days: int = 30) -> int:
    """Удалить старых подписчиков (старше keep_days дней)"""
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    
    deleted_count = db.query(models.InstagramFollower).filter(
        models.InstagramFollower.profile_id == profile_id,
        models.InstagramFollower.created_at < cutoff_date
    ).delete()
    
    db.commit()
    return deleted_count


# ===== АДМИН ПАНЕЛЬ: СТАТИСТИКА И УПРАВЛЕНИЕ =====

def get_total_users_count(db: Session) -> int:
    """Общее количество пользователей"""
    return db.query(models.User).count()


def get_active_users_count(db: Session, date: datetime) -> int:
    """Количество активных пользователей за определенную дату"""
    return db.query(models.User).filter(
        models.User.last_login >= date,
        models.User.is_active == True
    ).count()


def get_new_users_count(db: Session, date: datetime) -> int:
    """Количество новых пользователей за определенную дату"""
    return db.query(models.User).filter(
        models.User.created_at >= date
    ).count()


def get_total_profiles_count(db: Session) -> int:
    """Общее количество профилей"""
    return db.query(models.InstagramProfile).count()


def get_profiles_parsed_count(db: Session, date: datetime) -> int:
    """Количество профилей, спаршенных за определенную дату"""
    return db.query(models.InstagramProfile).filter(
        models.InstagramProfile.created_at >= date
    ).count()


def get_profiles_in_progress_count(db: Session) -> int:
    """Количество профилей в процессе парсинга"""
    return db.query(models.InstagramProfile).filter(
        models.InstagramProfile.parsing_status.in_(["pending", "processing"])
    ).count()


def get_total_subscriptions_count(db: Session) -> int:
    """Общее количество подписок"""
    return db.query(models.SubscriptionHistory).count()


def get_subscriptions_count(db: Session, date: datetime) -> int:
    """Количество подписок за определенную дату"""
    return db.query(models.SubscriptionHistory).filter(
        models.SubscriptionHistory.created_at >= date
    ).count()


def get_active_subscriptions_count(db: Session) -> int:
    """Количество активных подписок"""
    return db.query(models.SubscriptionHistory).filter(
        models.SubscriptionHistory.status == "active"
    ).count()


def get_revenue(db: Session, date: datetime) -> float:
    """Доходы за определенную дату"""
    result = db.query(func.sum(models.Payment.amount)).filter(
        models.Payment.created_at >= date,
        models.Payment.status == "completed"
    ).scalar()
    return result or 0.0


def get_tariff_statistics(db: Session) -> List[Dict]:
    """Статистика по тарифам"""
    from sqlalchemy import func
    
    result = db.query(
        models.Tariff.name,
        models.Tariff.price,
        func.count(models.SubscriptionHistory.id).label('subscriptions_count'),
        func.sum(models.Payment.amount).label('total_revenue')
    ).outerjoin(
        models.SubscriptionHistory, models.Tariff.id == models.SubscriptionHistory.tariff_id
    ).outerjoin(
        models.Payment, models.Tariff.id == models.Payment.tariff_id
    ).filter(
        models.Payment.status == "completed"
    ).group_by(models.Tariff.id).all()
    
    return [
        {
            "name": r.name,
            "price": r.price,
            "subscriptions": r.subscriptions_count or 0,
            "revenue": r.total_revenue or 0.0
        }
        for r in result
    ]


def get_parsing_statistics(db: Session) -> Dict:
    """Статистика парсинга"""
    from sqlalchemy import func
    
    total = db.query(models.InstagramProfile).count()
    completed = db.query(models.InstagramProfile).filter(
        models.InstagramProfile.parsing_status == "completed"
    ).count()
    failed = db.query(models.InstagramProfile).filter(
        models.InstagramProfile.parsing_status == "failed"
    ).count()
    processing = db.query(models.InstagramProfile).filter(
        models.InstagramProfile.parsing_status.in_(["pending", "processing"])
    ).count()
    
    avg_followers = db.query(func.avg(models.InstagramProfile.followers_count)).scalar() or 0
    
    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "processing": processing,
        "success_rate": round((completed / max(total, 1)) * 100, 2),
        "avg_followers": round(avg_followers, 0)
    }


def get_users_with_stats(db: Session, page: int = 1, search: Optional[str] = None, 
                        page_size: int = 50, sort: Optional[str] = None) -> List[Dict]:
    """Получить пользователей со статистикой для админки"""
    from sqlalchemy import func
    
    query = db.query(
        models.User,
        func.count(models.InstagramProfile.id).label('profiles_count'),
        models.Tariff.name.label('tariff_name'),
        models.InstagramProfile.username.label('ig_username'),
        models.InstagramProfile.full_name.label('ig_full_name')
    ).outerjoin(
        models.InstagramProfile, models.User.user_id == models.InstagramProfile.username  # Связь через парсинг
    ).outerjoin(
        models.Tariff, models.User.current_tariff_id == models.Tariff.id
    ).group_by(models.User.id, models.InstagramProfile.username, models.InstagramProfile.full_name)
    
    if search:
        query = query.filter(models.User.user_id.ilike(f"%{search}%"))
    
    # Добавляем сортировку
    if sort == "created_asc":
        query = query.order_by(models.User.created_at.asc())
    elif sort == "created_desc":
        query = query.order_by(models.User.created_at.desc())
    elif sort == "active_desc":
        query = query.order_by(models.User.is_active.desc(), models.User.last_login.desc())
    elif sort == "requests_desc":
        query = query.order_by(func.count(models.InstagramProfile.id).desc())
    else:  # created_desc по умолчанию
        query = query.order_by(models.User.created_at.desc())
    
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()
    
    result = []
    for user, profiles_count, tariff_name, ig_username, ig_full_name in users:
        # Проверяем активную подписку
        has_subscription = has_active_subscription(db, user.user_id)
        
        # Если есть подписка, но тариф не определён через JOIN, получаем его напрямую
        if has_subscription and not tariff_name and user.current_tariff_id:
            tariff = get_tariff_by_id(db, user.current_tariff_id)
            tariff_name = tariff.name if tariff else "Без подписки"
        elif not has_subscription:
            tariff_name = "Без подписки"
        elif not tariff_name:
            tariff_name = "Без подписки"
        
        # Формируем отображаемое имя
        display_name = format_user_display_name(user, ig_username, ig_full_name)
        
        result.append({
            "user": user,
            "profiles_count": profiles_count or 0,
            "tariff_name": tariff_name,
            "has_active_subscription": has_subscription,
            "subscription_end": user.subscription_end,
            "display_name": display_name,
            "ig_username": ig_username,
            "ig_full_name": ig_full_name
        })
    
    return result


def delete_user_completely(db: Session, user_id: str) -> bool:
    """Полное удаление пользователя и всех связанных данных"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    try:
        # Удаляем связанные данные
        db.query(models.SubscriptionHistory).filter(models.SubscriptionHistory.user_id == user_id).delete()
        db.query(models.Payment).filter(models.Payment.user_id == user_id).delete()
        db.query(models.SupportRequest).filter(models.SupportRequest.user_id == user_id).delete()
        
        # Удаляем уведомления
        try:
            db.query(models.NotificationSchedule).filter(models.NotificationSchedule.user_id == user_id).delete()
        except Exception as e:
            print(f"Warning: Could not delete notifications: {e}")
        
        # Удаляем активности
        try:
            db.query(models.UserActivity).filter(models.UserActivity.user_id == user_id).delete()
        except Exception as e:
            print(f"Warning: Could not delete activities: {e}")
        
        # Удаляем пользователя
        db.delete(user)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e


def update_user_tariff(db: Session, user_id: str, tariff_id: int) -> bool:
    """Обновить тариф пользователя"""
    user = get_user_by_id(db, user_id)
    tariff = get_tariff_by_id(db, tariff_id)
    
    if not user or not tariff:
        return False
    
    user.current_tariff_id = tariff_id
    user.is_paid = True
    
    # Если это временная подписка
    if tariff.duration_days:
        user.subscription_start = datetime.now()
        user.subscription_end = datetime.now() + timedelta(days=tariff.duration_days)
    
    # Если это комбо план
    if tariff.requests_count:
        user.remaining_requests = tariff.requests_count
    
    db.commit()
    return True


def update_user_details(db: Session, user_id: str, user_data: dict) -> bool:
    """Обновить детальную информацию пользователя"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    try:
        # Обновляем основные поля
        if 'is_active' in user_data:
            user.is_active = user_data['is_active']
        
        if 'is_paid' in user_data:
            user.is_paid = user_data['is_paid']
        
        if 'current_tariff_id' in user_data:
            user.current_tariff_id = user_data['current_tariff_id']
        
        if 'remaining_requests' in user_data:
            user.remaining_requests = user_data['remaining_requests']
        
        # Обновляем даты подписки
        if 'subscription_start' in user_data and user_data['subscription_start']:
            user.subscription_start = datetime.fromisoformat(user_data['subscription_start'].replace('T', ' '))
        elif 'subscription_start' in user_data and not user_data['subscription_start']:
            user.subscription_start = None
        
        if 'subscription_end' in user_data and user_data['subscription_end']:
            user.subscription_end = datetime.fromisoformat(user_data['subscription_end'].replace('T', ' '))
        elif 'subscription_end' in user_data and not user_data['subscription_end']:
            user.subscription_end = None
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e


def get_profiles_with_details(db: Session, page: int = 1, search: Optional[str] = None, 
                            status: Optional[str] = None, page_size: int = 30, sort: Optional[str] = None) -> List[Dict]:
    """Получить профили с деталями для админки"""
    from sqlalchemy import func
    
    query = db.query(
        models.InstagramProfile,
        func.count(models.InstagramFollower.id).label('followers_saved')
    ).outerjoin(
        models.InstagramFollower, models.InstagramProfile.id == models.InstagramFollower.profile_id
    ).group_by(models.InstagramProfile.id)
    
    if search:
        query = query.filter(models.InstagramProfile.username.ilike(f"%{search}%"))
    
    if status:
        query = query.filter(models.InstagramProfile.parsing_status == status)
    
    # Добавляем сортировку
    if sort == "created_asc":
        query = query.order_by(models.InstagramProfile.created_at.asc())
    elif sort == "created_desc":
        query = query.order_by(models.InstagramProfile.created_at.desc())
    elif sort == "followers_desc":
        query = query.order_by(models.InstagramProfile.followers_count.desc())
    elif sort == "success_desc":
        query = query.order_by((func.count(models.InstagramFollower.id) / func.coalesce(models.InstagramProfile.followers_count, 1)).desc())
    elif sort == "updated_desc":
        query = query.order_by(models.InstagramProfile.last_scraped.desc())
    else:  # created_desc по умолчанию
        query = query.order_by(models.InstagramProfile.created_at.desc())
    
    offset = (page - 1) * page_size
    profiles = query.offset(offset).limit(page_size).all()
    
    result = []
    for profile, followers_saved in profiles:
        result.append({
            "profile": profile,
            "followers_saved": followers_saved or 0,
            "success_rate": round((followers_saved or 0) / max(profile.followers_count or 1, 1) * 100, 2) if profile.followers_count else 0
        })
    
    return result


def get_profile_full_details(db: Session, profile_id: int) -> Optional[models.InstagramProfile]:
    """Получить полную информацию о профиле"""
    return db.query(models.InstagramProfile).filter(models.InstagramProfile.id == profile_id).first()


def get_profile_followers_count(db: Session, profile_id: int) -> int:
    """Количество сохраненных подписчиков профиля"""
    return db.query(models.InstagramFollower).filter(models.InstagramFollower.profile_id == profile_id).count()


def get_profile_mutual_followers(db: Session, profile_id: int) -> List[models.InstagramFollower]:
    """Получить взаимных подписчиков профиля"""
    return db.query(models.InstagramFollower).filter(
        models.InstagramFollower.profile_id == profile_id
    ).limit(10).all()


def get_profile_parsing_history(db: Session, profile_id: int) -> List[Dict]:
    """История парсинга профиля"""
    profile = get_profile_full_details(db, profile_id)
    if not profile:
        return []
    
    return [
        {
            "timestamp": profile.created_at,
            "status": "created",
            "message": "Профиль создан"
        },
        {
            "timestamp": profile.last_scraped,
            "status": profile.parsing_status,
            "message": f"Статус парсинга: {profile.parsing_status}"
        }
    ]


def get_detailed_subscription_statistics(db: Session) -> Dict:
    """Детальная статистика по подпискам"""
    from sqlalchemy import func
    
    # Общая статистика
    total = db.query(models.SubscriptionHistory).count()
    active = db.query(models.SubscriptionHistory).filter(models.SubscriptionHistory.status == "active").count()
    paused = db.query(models.SubscriptionHistory).filter(models.SubscriptionHistory.status == "paused").count()
    cancelled = db.query(models.SubscriptionHistory).filter(models.SubscriptionHistory.status == "cancelled").count()
    
    # Статистика по тарифам
    tariff_breakdown = db.query(
        models.Tariff.name,
        func.count(models.SubscriptionHistory.id).label('count'),
        func.sum(models.Tariff.price).label('revenue')
    ).join(
        models.SubscriptionHistory, models.Tariff.id == models.SubscriptionHistory.tariff_id
    ).group_by(models.Tariff.id).all()
    
    return {
        "total": total,
        "active": active,
        "paused": paused,
        "cancelled": cancelled,
        "conversion_rate": round((total / max(get_total_users_count(db), 1)) * 100, 2),
        "tariff_breakdown": [
            {"name": r.name, "count": r.count, "revenue": r.revenue or 0}
            for r in tariff_breakdown
        ]
    }


def get_tariff_performance_stats(db: Session) -> List[Dict]:
    """Статистика производительности тарифов"""
    from sqlalchemy import func
    
    return db.query(
        models.Tariff.name,
        models.Tariff.price,
        func.count(models.SubscriptionHistory.id).label('total_subscriptions'),
        func.count(models.SubscriptionHistory.id).filter(
            models.SubscriptionHistory.status == "active"
        ).label('active_subscriptions'),
        func.avg(
            func.extract('epoch', models.SubscriptionHistory.end_date - models.SubscriptionHistory.start_date) / 86400
        ).label('avg_duration_days')
    ).outerjoin(
        models.SubscriptionHistory, models.Tariff.id == models.SubscriptionHistory.tariff_id
    ).group_by(models.Tariff.id).all()


def get_revenue_by_tariff(db: Session) -> List[Dict]:
    """Доходы по тарифам"""
    from sqlalchemy import func
    
    result = db.query(
        models.Tariff.name,
        func.sum(models.Payment.amount).label('total_revenue'),
        func.count(models.Payment.id).label('payment_count'),
        func.avg(models.Payment.amount).label('avg_payment')
    ).join(
        models.Payment, models.Tariff.id == models.Payment.tariff_id
    ).filter(
        models.Payment.status == "completed"
    ).group_by(models.Tariff.id).all()
    
    return [
        {
            "name": r.name,
            "total_revenue": r.total_revenue or 0,
            "payment_count": r.payment_count or 0,
            "avg_payment": r.avg_payment or 0
        }
        for r in result
    ]


def search_users(db: Session, query: str, limit: int = 10) -> List[models.User]:
    """Поиск пользователей для автокомплита"""
    return db.query(models.User).filter(
        models.User.user_id.ilike(f"%{query}%")
    ).limit(limit).all()


def search_profiles(db: Session, query: str, limit: int = 10) -> List[models.InstagramProfile]:
    """Поиск профилей для автокомплита"""
    return db.query(models.InstagramProfile).filter(
        models.InstagramProfile.username.ilike(f"%{query}%")
    ).limit(limit).all()


def trigger_profile_reparse(db: Session, profile_id: int) -> bool:
    """Запустить повторный парсинг профиля"""
    profile = get_profile_full_details(db, profile_id)
    if not profile:
        return False
    
    # Сбрасываем статус для повторного парсинга
    profile.parsing_status = "pending"
    profile.parse_task_id = None
    
    db.commit()
    
    # Здесь можно добавить логику запуска парсинга
    # add_parse_task(profile.username, profile.user_id)
    
    return True


# ===== ФУНКЦИИ ДЛЯ ВИРТУАЛЬНОГО СКРОЛЛА =====

def get_users_virtual_scroll(db: Session, offset: int = 0, limit: int = 100, 
                           search: Optional[str] = None, sort: Optional[str] = None) -> List[Dict]:
    """Получить пользователей для виртуального скролла"""
    from sqlalchemy import func
    
    query = db.query(
        models.User,
        func.count(models.InstagramProfile.id).label('profiles_count'),
        models.Tariff.name.label('tariff_name'),
        models.InstagramProfile.username.label('ig_username'),
        models.InstagramProfile.full_name.label('ig_full_name')
    ).outerjoin(
        models.InstagramProfile, models.User.user_id == models.InstagramProfile.username
    ).outerjoin(
        models.Tariff, models.User.current_tariff_id == models.Tariff.id
    ).group_by(models.User.id, models.InstagramProfile.username, models.InstagramProfile.full_name)
    
    if search:
        query = query.filter(models.User.user_id.ilike(f"%{search}%"))
    
    # Сортировка
    if sort == "created_asc":
        query = query.order_by(models.User.created_at.asc())
    elif sort == "created_desc":
        query = query.order_by(models.User.created_at.desc())
    elif sort == "active_desc":
        query = query.order_by(models.User.is_active.desc(), models.User.last_login.desc())
    elif sort == "requests_desc":
        query = query.order_by(func.count(models.InstagramProfile.id).desc())
    else:
        query = query.order_by(models.User.created_at.desc())
    
    users = query.offset(offset).limit(limit).all()
    
    result = []
    for user, profiles_count, tariff_name, ig_username, ig_full_name in users:
        try:
            active_subscription = get_user_active_subscription(db, user.user_id)
            has_active_subscription = active_subscription is not None
        except Exception:
            has_active_subscription = user.is_paid  # Fallback на текущий статус
        
        # Формируем отображаемое имя
        display_name = format_user_display_name(user, ig_username, ig_full_name)
        
        result.append({
            "user": user,
            "profiles_count": profiles_count or 0,
            "tariff_name": tariff_name or "Без подписки",
            "has_active_subscription": has_active_subscription,
            "subscription_end": user.subscription_end,
            "display_name": display_name,
            "ig_username": ig_username,
            "ig_full_name": ig_full_name
        })
    
    return result


def get_profiles_virtual_scroll(db: Session, offset: int = 0, limit: int = 100,
                               search: Optional[str] = None, status: Optional[str] = None, 
                               sort: Optional[str] = None) -> List[Dict]:
    """Получить профили для виртуального скролла"""
    from sqlalchemy import func
    
    query = db.query(
        models.InstagramProfile,
        func.count(models.InstagramFollower.id).label('followers_saved')
    ).outerjoin(
        models.InstagramFollower, models.InstagramProfile.id == models.InstagramFollower.profile_id
    ).group_by(models.InstagramProfile.id)
    
    if search:
        query = query.filter(models.InstagramProfile.username.ilike(f"%{search}%"))
    
    if status:
        query = query.filter(models.InstagramProfile.parsing_status == status)
    
    # Сортировка
    if sort == "created_asc":
        query = query.order_by(models.InstagramProfile.created_at.asc())
    elif sort == "created_desc":
        query = query.order_by(models.InstagramProfile.created_at.desc())
    elif sort == "followers_desc":
        query = query.order_by(models.InstagramProfile.followers_count.desc())
    elif sort == "success_desc":
        query = query.order_by((func.count(models.InstagramFollower.id) / func.coalesce(models.InstagramProfile.followers_count, 1)).desc())
    elif sort == "updated_desc":
        query = query.order_by(models.InstagramProfile.last_scraped.desc())
    else:
        query = query.order_by(models.InstagramProfile.created_at.desc())
    
    profiles = query.offset(offset).limit(limit).all()
    
    result = []
    for profile, followers_saved in profiles:
        result.append({
            "profile": profile,
            "followers_saved": followers_saved or 0,
            "success_rate": round((followers_saved or 0) / max(profile.followers_count or 1, 1) * 100, 2) if profile.followers_count else 0
        })
    
    return result


def format_user_display_name(user, ig_username: Optional[str] = None, ig_full_name: Optional[str] = None) -> str:
    """Формирует красивое отображаемое имя пользователя с приоритетом: Telegram > Instagram > ID"""
    if user.first_name or user.last_name:
        # Используем Telegram данные
        tg_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if user.telegram_username:
            return f"{tg_name} (@{user.telegram_username})"
        else:
            return tg_name
    elif ig_full_name:
        # Используем Instagram данные
        return f"{ig_full_name} (@{ig_username})" if ig_username else ig_full_name
    elif ig_username:
        return f"@{ig_username}"
    elif user.telegram_username:
        return f"@{user.telegram_username}"
    else:
        return user.user_id


def get_users_for_broadcast(db: Session, limit: int = 1000) -> List[Dict]:
    """Получить пользователей для рассылки с их Instagram данными"""
    from sqlalchemy import func
    
    query = db.query(
        models.User,
        models.InstagramProfile.username.label('ig_username'),
        models.InstagramProfile.full_name.label('ig_full_name'),
        func.count(models.InstagramProfile.id).label('profiles_count')
    ).outerjoin(
        models.InstagramProfile, models.User.user_id == models.InstagramProfile.username
    ).group_by(models.User.id, models.InstagramProfile.username, models.InstagramProfile.full_name)
    
    # Получаем только активных пользователей
    query = query.filter(models.User.is_active == True)
    
    users = query.limit(limit).all()
    
    result = []
    for user, ig_username, ig_full_name, profiles_count in users:
        display_name = format_user_display_name(user, ig_username, ig_full_name)
        
        result.append({
            "user_id": user.user_id,
            "display_name": display_name,
            "ig_username": ig_username,
            "ig_full_name": ig_full_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "telegram_username": user.telegram_username,
            "profiles_count": profiles_count or 0,
            "has_subscription": user.is_paid,
            "is_active": user.is_active
        })
    
    return result


def update_user_telegram_data(db: Session, user_id: str, first_name: Optional[str] = None, 
                             last_name: Optional[str] = None, telegram_username: Optional[str] = None) -> bool:
    """Обновить Telegram данные пользователя"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if telegram_username is not None:
        user.telegram_username = telegram_username
    
    try:
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def create_test_telegram_users(db: Session) -> bool:
    """Создать тестовых пользователей с Telegram данными для демонстрации"""
    test_users = [
        {"user_id": "demo_user_1", "first_name": "Александр", "last_name": "Петров", "telegram_username": "alex_petrov"},
        {"user_id": "demo_user_2", "first_name": "Мария", "last_name": "Иванова", "telegram_username": "maria_iv"},
        {"user_id": "demo_user_3", "first_name": "Дмитрий", "last_name": None, "telegram_username": "dmitry_dev"},
        {"user_id": "demo_user_4", "first_name": "Анна", "last_name": "Смирнова", "telegram_username": None},
    ]
    
    try:
        for user_data in test_users:
            existing_user = get_user_by_id(db, user_data["user_id"])
            if not existing_user:
                # Создаем нового пользователя
                new_user = models.User(
                    user_id=user_data["user_id"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    telegram_username=user_data["telegram_username"],
                    is_active=True
                )
                db.add(new_user)
            else:
                # Обновляем существующего
                existing_user.first_name = user_data["first_name"]
                existing_user.last_name = user_data["last_name"]
                existing_user.telegram_username = user_data["telegram_username"]
        
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False