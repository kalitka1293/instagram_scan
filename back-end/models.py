from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime


class User(Base):
    """Модель пользователя сервиса"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    user_id = Column(String(50), unique=True, index=True, nullable=False)  # Уникальный ID пользователя
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Telegram данные пользователя
    first_name = Column(String(100), nullable=True)  # Имя из Telegram
    last_name = Column(String(100), nullable=True)   # Фамилия из Telegram
    telegram_username = Column(String(100), nullable=True)  # Username из Telegram (@username)
    
    # Подписка и оплата
    is_paid = Column(Boolean, default=False)
    current_tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=True)
    subscription_start = Column(DateTime(timezone=True), nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Дополнительная информация
    last_login = Column(DateTime(timezone=True), nullable=True)
    total_requests = Column(Integer, default=0)  # Общее количество запросов
    remaining_requests = Column(Integer, default=0)  # Оставшиеся запросы для комбо тарифов
    
    # Связи
    current_tariff = relationship("Tariff", back_populates="users")
    payments = relationship("Payment", back_populates="user")
    subscription_history = relationship("SubscriptionHistory", back_populates="user")
    support_requests = relationship("SupportRequest", back_populates="user")
    activities = relationship("UserActivity", back_populates="user")
    scheduled_notifications = relationship("NotificationSchedule", back_populates="user")


class Tariff(Base):
    """Модель тарифных планов"""
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация о тарифе
    name = Column(String(100), unique=True, index=True, nullable=False)
    price = Column(Float, nullable=False)  # Цена в рублях
    duration_days = Column(Integer, nullable=True)  # Количество дней, NULL для комбо планов
    requests_count = Column(Integer, nullable=True)  # Количество запросов для комбо планов
    
    # Описание тарифа
    subtitle = Column(Text, nullable=True)
    features = Column(JSON, nullable=True)  # Список функций в JSON формате
    
    # Настройки тарифа
    is_active = Column(Boolean, default=True)
    is_demo = Column(Boolean, default=False)
    auto_renewal = Column(Boolean, default=False)  # Автопродление
    
    # Дополнительные параметры
    next_tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=True)  # Следующий тариф для демо
    next_tariff_price = Column(Float, nullable=True)  # Цена следующего тарифа
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    users = relationship("User", back_populates="current_tariff")
    next_tariff = relationship("Tariff", remote_side=[id])
    payments = relationship("Payment", back_populates="tariff")
    subscription_history = relationship("SubscriptionHistory", foreign_keys="SubscriptionHistory.tariff_id", back_populates="tariff")


class InstagramProfile(Base):
    """Модель для кэширования данных Instagram профилей"""
    __tablename__ = "instagram_profiles"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация профиля
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=True)
    biography = Column(Text, nullable=True)
    external_url = Column(String(500), nullable=True)
    
    # Статистика профиля
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    
    # Флаги профиля
    is_verified = Column(Boolean, default=False)
    is_private = Column(Boolean, default=False)
    is_business = Column(Boolean, default=False)
    
    # Аналитические данные в JSON формате
    analytics_data = Column(JSON, nullable=True)  # Полная аналитика из фронтенда
    posts_data = Column(JSON, nullable=True)      # Данные о постах
    stats_data = Column(JSON, nullable=True)      # Статистика
    comments_data = Column(JSON, nullable=True)   # Данные о комментариях
    
    # Метаданные
    profile_pic_url = Column(String(500), nullable=True)
    last_scraped = Column(DateTime(timezone=True), server_default=func.now())
    scrape_count = Column(Integer, default=1)  # Сколько раз запрашивали этот профиль
    is_data_fresh = Column(Boolean, default=True)  # Актуальны ли данные
    
    # Асинхронный парсинг
    parsing_status = Column(String(20), default="completed")  # pending, processing, completed, failed
    parse_task_id = Column(String(100), nullable=True)  # ID задачи парсинга
    followers_parsed_at = Column(DateTime(timezone=True), nullable=True)
    followings_parsed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    followers = relationship("InstagramFollower", back_populates="profile")


class InstagramFollower(Base):
    """Модель для сохранения подписчиков Instagram профилей"""
    __tablename__ = "instagram_followers"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связь с профилем
    profile_id = Column(Integer, ForeignKey("instagram_profiles.id"), nullable=False)
    
    # Данные подписчика из Instagram API
    follower_pk = Column(String(50), nullable=False)  # ID из Instagram
    username = Column(String(100), nullable=False)
    full_name = Column(String(200))
    profile_pic_url = Column(Text)
    profile_pic_url_local = Column(String(500), nullable=True)  # Локальный путь к сохранённой аватарке
    
    # Флаги подписчика
    is_verified = Column(Boolean, default=False)
    is_private = Column(Boolean, default=False)
    has_anonymous_profile_picture = Column(Boolean, default=False)
    
    # Дополнительные данные
    fbid_v2 = Column(String(100), nullable=True)
    third_party_downloads_enabled = Column(Boolean, default=False)
    latest_reel_media = Column(String(50), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    profile = relationship("InstagramProfile", back_populates="followers")

    __table_args__ = (
        UniqueConstraint('profile_id', 'follower_pk', name='_profile_follower_uc'),
    )


class Payment(Base):
    """Модель для отслеживания платежей"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация о платеже
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=False)
    
    # Детали платежа
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    payment_method = Column(String(50), default="cloudpayments")
    
    # Статус платежа
    status = Column(String(20), default="pending")  # pending, completed, failed, refunded
    transaction_id = Column(String(200), nullable=True)  # ID транзакции от CloudPayments
    
    # CloudPayments данные
    cloudpayments_transaction_id = Column(String(100), nullable=True)
    cloudpayments_invoice_id = Column(String(100), nullable=True)
    card_token = Column(String(200), nullable=True)  # Токен карты для рекуррентных платежей
    
    # Данные карты
    card_first_six = Column(String(6), nullable=True)
    card_last_four = Column(String(4), nullable=True)
    card_type = Column(String(20), nullable=True)  # Visa, MasterCard, etc.
    
    # Рекуррентные платежи
    is_recurrent = Column(Boolean, default=False)
    subscription_id = Column(String(100), nullable=True)  # ID подписки в CloudPayments
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    user = relationship("User", back_populates="payments")
    tariff = relationship("Tariff", back_populates="payments")


class SubscriptionHistory(Base):
    """История подписок пользователя"""
    __tablename__ = "subscription_history"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=False)
    
    # Период подписки
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Статус подписки
    status = Column(String(20), default="active")  # active, paused, cancelled, expired
    pause_days_used = Column(Integer, default=0)  # Использованные дни паузы
    
    # CloudPayments данные
    cloudpayments_subscription_id = Column(String(100), nullable=True)  # ID подписки в CloudPayments
    card_token = Column(String(200), nullable=True)  # Токен карты
    auto_renewal = Column(Boolean, default=False)  # Автопродление
    failed_attempts = Column(Integer, default=0)  # Количество неудачных списаний
    last_payment_attempt = Column(DateTime(timezone=True), nullable=True)
    next_payment_date = Column(DateTime(timezone=True), nullable=True)
    
    # Каскадное понижение тарифа
    original_tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=True)  # Оригинальный тариф
    downgrade_attempts = Column(Integer, default=0)  # Попытки понижения тарифа
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("User", back_populates="subscription_history")
    tariff = relationship("Tariff", foreign_keys=[tariff_id], back_populates="subscription_history")
    original_tariff = relationship("Tariff", foreign_keys=[original_tariff_id])


class SupportRequest(Base):
    """Модель для обращений в поддержку"""
    __tablename__ = "support_requests"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=True)
    email = Column(String(200), nullable=True)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Статус обращения
    status = Column(String(20), default="open")  # open, in_progress, closed
    priority = Column(String(10), default="normal")  # low, normal, high, urgent
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    user = relationship("User", back_populates="support_requests")


class UserActivity(Base):
    """Модель активности пользователя для планирования уведомлений"""
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    
    # Тип активности: app_start, app_exit, profile_parse, etc.
    activity_type = Column(String(50), nullable=False)
    
    # Время активности
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Дополнительные данные (например, username профиля)
    extra_data = Column(JSON, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="activities")


class NotificationSchedule(Base):
    """Модель запланированных уведомлений"""
    __tablename__ = "notification_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    
    # Тип уведомления: like, follower
    notification_type = Column(String(50), nullable=False)
    
    # Время когда нужно отправить
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    
    # Статус отправки
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Instagram профиль для уведомления
    profile_username = Column(String(100), nullable=True)
    
    # Текст уведомления
    message_text = Column(Text, nullable=True)
    button_text = Column(String(100), nullable=True)
    button_url = Column(String(500), nullable=True)
    
    # Метки времени
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Ошибки отправки
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Связи  
    user = relationship("User", back_populates="scheduled_notifications")