from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# === USER SCHEMAS ===
class UserBase(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=50)

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    is_paid: Optional[bool] = None
    current_tariff_id: Optional[int] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    is_active: Optional[bool] = None
    remaining_requests: Optional[int] = None

class User(UserBase):
    id: int
    is_paid: bool
    current_tariff_id: Optional[int] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    is_active: bool
    last_login: Optional[datetime] = None
    total_requests: int
    remaining_requests: Optional[int] = None  # ✅ Может быть None для безлимитных тарифов
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# === TARIFF SCHEMAS ===
class TariffBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    duration_days: Optional[int] = Field(None, gt=0)
    requests_count: Optional[int] = Field(None, gt=0)
    subtitle: Optional[str] = None
    features: Optional[List[str]] = None

class TariffCreate(TariffBase):
    is_active: bool = True
    is_demo: bool = False
    auto_renewal: bool = False
    next_tariff_id: Optional[int] = None
    next_tariff_price: Optional[float] = None

class TariffUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    duration_days: Optional[int] = None
    requests_count: Optional[int] = None
    subtitle: Optional[str] = None
    features: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_demo: Optional[bool] = None
    auto_renewal: Optional[bool] = None

class Tariff(TariffBase):
    id: int
    is_active: bool
    is_demo: bool
    auto_renewal: bool
    next_tariff_id: Optional[int] = None
    next_tariff_price: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# === INSTAGRAM PROFILE SCHEMAS ===
class InstagramProfileBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)

class InstagramProfileCreate(InstagramProfileBase):
    full_name: Optional[str] = None
    biography: Optional[str] = None
    external_url: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    is_verified: bool = False
    is_private: bool = False
    is_business: bool = False
    analytics_data: Optional[Dict[str, Any]] = None
    posts_data: Optional[List[Dict[str, Any]]] = None
    stats_data: Optional[Dict[str, Any]] = None
    profile_pic_url: Optional[str] = None
    parsing_status: str = "pending"
    parse_task_id: Optional[str] = None

class InstagramProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    biography: Optional[str] = None
    external_url: Optional[str] = None
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    posts_count: Optional[int] = None
    is_verified: Optional[bool] = None
    is_private: Optional[bool] = None
    is_business: Optional[bool] = None
    analytics_data: Optional[Dict[str, Any]] = None
    posts_data: Optional[List[Dict[str, Any]]] = None
    stats_data: Optional[Dict[str, Any]] = None
    profile_pic_url: Optional[str] = None
    is_data_fresh: Optional[bool] = None

class InstagramProfile(InstagramProfileBase):
    id: int
    full_name: Optional[str] = None
    biography: Optional[str] = None
    external_url: Optional[str] = None
    followers_count: int
    following_count: int
    posts_count: int
    is_verified: bool
    is_private: bool
    is_business: bool
    analytics_data: Optional[Dict[str, Any]] = None
    posts_data: Optional[List[Dict[str, Any]]] = None
    stats_data: Optional[Dict[str, Any]] = None
    profile_pic_url: Optional[str] = None
    last_scraped: datetime
    scrape_count: int
    is_data_fresh: bool
    parsing_status: str
    parse_task_id: Optional[str] = None
    followers_parsed_at: Optional[datetime] = None
    followings_parsed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# === PAYMENT SCHEMAS ===
class PaymentBase(BaseModel):
    user_id: str
    tariff_id: int
    amount: float = Field(..., gt=0)
    currency: str = "RUB"
    payment_method: Optional[str] = None

class PaymentCreate(PaymentBase):
    card_first_six: Optional[str] = Field(None, min_length=6, max_length=6)
    card_last_four: Optional[str] = Field(None, min_length=4, max_length=4)

class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None

class Payment(PaymentBase):
    id: int
    status: str
    transaction_id: Optional[str] = None
    card_first_six: Optional[str] = None
    card_last_four: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# === SUBSCRIPTION HISTORY SCHEMAS ===
class SubscriptionHistoryBase(BaseModel):
    user_id: str
    tariff_id: int
    start_date: datetime
    end_date: Optional[datetime] = None

class SubscriptionHistoryCreate(SubscriptionHistoryBase):
    status: str = "active"

class SubscriptionHistoryUpdate(BaseModel):
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    pause_days_used: Optional[int] = None

class SubscriptionHistory(SubscriptionHistoryBase):
    id: int
    status: str
    pause_days_used: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === SUPPORT REQUEST SCHEMAS ===
class SupportRequestBase(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)

class SupportRequestCreate(SupportRequestBase):
    user_id: Optional[str] = None
    email: Optional[str] = None

class SupportRequestUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    resolved_at: Optional[datetime] = None

class SupportRequest(SupportRequestBase):
    id: int
    user_id: Optional[str] = None
    email: Optional[str] = None
    status: str
    priority: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# === AUTH SCHEMAS ===
class AuthRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=50)

class UserLoginRequest(BaseModel):
    user_id: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[User] = None
    is_new_user: bool = False

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[User] = None

# ===== USER ACTIVITIES SCHEMAS =====

class UserActivity(BaseModel):
    username: str
    full_name: str
    profile_pic_url: Optional[str] = None
    action: str  # Описание действия
    status: str  # Статус (Новый!, Сейчас, 2 мин назад, и т.д.)
    timestamp: Optional[str] = None

class UserActivities(BaseModel):
    recent_likes: List[UserActivity]
    recent_follows: List[UserActivity]
    recent_comments: List[UserActivity]
    recent_messages: List[UserActivity]
    recent_sent_comments: List[UserActivity] = []

# === REQUEST/RESPONSE SCHEMAS ===
class ProfileCheckRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_.]+$')
    user_id: Optional[str] = None  # Добавляем для связи с пользователем

class ProfileCheckResponse(BaseModel):
    success: bool
    message: str
    profile: Optional[InstagramProfile] = None
    analytics_data: Optional[Dict[str, Any]] = None
    posts_data: Optional[List[Dict[str, Any]]] = None
    comments_data: Optional[List[Dict[str, Any]]] = None
    user_activities: Optional[UserActivities] = None
    has_active_subscription: bool = False

class AnalyticsResponse(BaseModel):
    success: bool
    analytics_data: Optional[Dict[str, Any]] = None
    message: str

class StatsResponse(BaseModel):
    success: bool
    stats_data: Optional[Dict[str, Any]] = None
    message: str

class SubscriptionRequest(BaseModel):
    user_id: str
    tariff_id: int
    card_cryptogram: Optional[str] = None  # Криптограмма карты от CloudPayments виджета (опционально)
    name: Optional[str] = None  # Имя плательщика
    email: Optional[str] = None  # Email плательщика
    transaction_id: Optional[str] = None  # ID транзакции CloudPayments
    card_token: Optional[str] = None  # Токен карты для рекуррентных платежей

class SubscriptionResponse(BaseModel):
    success: bool
    message: str
    subscription: Optional[SubscriptionHistory] = None

class PauseSubscriptionRequest(BaseModel):
    user_id: str

class CancelSubscriptionRequest(BaseModel):
    user_id: str
    card_first_six: str = Field(..., min_length=6, max_length=6)
    card_last_four: str = Field(..., min_length=4, max_length=4)
    account_id: str
    reason: str


# === ASYNC PARSING SCHEMAS ===

class ParseTaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class FollowersResponse(BaseModel):
    success: bool
    message: str
    status: str  # pending, completed
    task_id: Optional[str] = None
    followers: Optional[List[Dict[str, Any]]] = None
    mutual_followers: Optional[List[Dict[str, Any]]] = None


# ===== INSTAGRAM FOLLOWERS SCHEMAS =====

class InstagramFollowerCreate(BaseModel):
    follower_pk: str
    username: str
    full_name: Optional[str] = None
    profile_pic_url: Optional[str] = None
    is_verified: bool = False
    is_private: bool = False
    has_anonymous_profile_picture: bool = False
    fbid_v2: Optional[str] = None
    third_party_downloads_enabled: bool = False
    latest_reel_media: Optional[str] = None


class InstagramFollower(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    profile_id: int
    follower_pk: str
    username: str
    full_name: Optional[str]
    profile_pic_url: Optional[str]
    is_verified: bool
    is_private: bool
    has_anonymous_profile_picture: bool
    fbid_v2: Optional[str]
    third_party_downloads_enabled: bool
    latest_reel_media: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


