/**
 * API утилиты для работы с бэкендом InstardingBot
 */
//https://truck-tma.ru/
const API_BASE_URL =  'http://127.0.0.1:8008';
// const API_BASE_URL =  'https://insta.truck-tma.ru';

// Функция для получения прокси URL изображения
export const getProxyImageUrl = (url: string): string => {
  if (!url) return '/default-avatar.png';
  
  // Если это локальное изображение из storage, добавляем API_BASE_URL
  if (url.startsWith('/storage/')) {
    const fullUrl = `${API_BASE_URL}${url}`;
    console.log(`🖼️ Local image: ${url} → ${fullUrl}`);
    return fullUrl;
  }
  
  // Если это уже полный URL с нашим доменом, возвращаем как есть
  if (url.startsWith(API_BASE_URL) || url.startsWith('data:')) {
    return url;
  }
  
  // Для внешних URL Instagram используем прокси
  return `${API_BASE_URL}/api/proxy-image?url=${encodeURIComponent(url)}`;
};
// Типы для API ответов
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
}

export interface User {
  user_id: string;
  is_paid: boolean;
  current_tariff_id?: number;
  subscription_start?: string;
  subscription_end?: string;
  remaining_requests: number;
  last_login?: string;
}

export interface AuthResponse {
  success: boolean;
  message?: string;
  user?: User;
  token?: string;
}

export interface PostData {
  shortcode: string;
  url: string;
  caption: string;
  likes: number;
  comments: number;
  is_video: boolean;
  timestamp: string;
  thumbnail_url?: string;
}

export interface InstagramProfile {
  username: string;
  full_name?: string;
  biography?: string;
  followers_count: number;
  following_count: number;
  posts_count: number;
  profile_pic_url: string;
  is_verified: boolean;
  is_private: boolean;
  is_business: boolean;
  external_url?: string;
  last_scraped?: string;
  analytics_data?: any;
  posts_data?: PostData[];
  stats_data?: any;
}

export interface UserActivity {
  username: string;
  full_name: string;
  profile_pic_url?: string;
  action: string;
  status: string;
  timestamp?: string;
}

export interface UserActivities {
  recent_likes: UserActivity[];
  recent_follows: UserActivity[];
  recent_comments: UserActivity[];
  recent_messages: UserActivity[];
}

export interface ProfileCheckResponse {
  success: boolean;
  message?: string;
  profile?: InstagramProfile;
  analytics_data?: any;
  posts_data?: PostData[];
  comments_data?: any[];
  user_activities?: UserActivities;
  user_requests_remaining?: number;
  has_active_subscription?: boolean;
}

export interface ProfileAnalyticsResponse {
  success: boolean;
  message?: string;
  profile?: InstagramProfile;
  data?: any;
}

export interface Tariff {
  id: number;
  name: string;
  price: number;
  duration_days: number;
  requests_count: number;
  is_active: boolean;
}

export interface SubscriptionStatus {
  is_active: boolean;
  current_tariff?: Tariff;
  subscription_start?: string;
  subscription_end?: string;
  remaining_requests: number;
  days_left?: number;
}

// Общая функция для API запросов
async function apiRequest<T = any>(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE',
  endpoint: string,
  data?: any
): Promise<T> {
  try {
    const options: RequestInit = {
      method: method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (data) {
      options.body = JSON.stringify(data);
    }

    const response = await fetch(API_BASE_URL + endpoint, options);
    
    if (!response.ok) {
      // Пытаемся извлечь детали ошибки из ответа
      try {
        const errorData = await response.json();
        const errorMessage = errorData.detail || errorData.message || response.statusText;
        throw new Error(errorMessage);
      } catch (jsonError) {
        // Если не удалось распарсить JSON, используем стандартное сообщение
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// === АВТОРИЗАЦИЯ ===

export async function loginUser(userId: string): Promise<AuthResponse> {
  return await apiRequest<AuthResponse>('POST', '/api/auth/login', { user_id: userId });
}

export async function getUserInfo(userId: string): Promise<User> {
  return await apiRequest<User>('GET', `/api/auth/user/${userId}`);
}

// === INSTAGRAM ПРОФИЛИ ===

export async function checkInstagramProfile(username: string, userId: string): Promise<ProfileCheckResponse> {
  return await apiRequest<ProfileCheckResponse>('POST', '/api/profile/check', { 
    username: username, 
    user_id: userId 
  });
}

export async function getProfileAnalytics(username: string): Promise<ProfileAnalyticsResponse> {
  return await apiRequest<ProfileAnalyticsResponse>('GET', `/api/profile/${username}/analytics`);
}

export async function getProfileStats(username: string): Promise<ApiResponse<any>> {
  return await apiRequest<ApiResponse<any>>('GET', `/api/profile/${username}/stats`);
}

// === НОВЫЕ АСИНХРОННЫЕ ENDPOINTS ===

export interface FollowersResponse {
  success: boolean;
  message: string;
  status: string; // pending, processing, completed, failed
  task_id?: string;
  followers?: any[];
  mutual_followers?: any[];
}

export interface ParseStatusResponse {
  success: boolean;
  status: string;
  task_id?: string;
  message: string;
}

export async function getProfileFollowers(username: string): Promise<FollowersResponse> {
  return await apiRequest<FollowersResponse>('GET', `/api/profile/${username}/followers`);
}

export async function getParseStatus(username: string): Promise<ParseStatusResponse> {
  return await apiRequest<ParseStatusResponse>('GET', `/api/profile/${username}/parse-status`);
}

// === ТАРИФЫ ===

export async function getTariffs(): Promise<Tariff[]> {
  return await apiRequest<Tariff[]>('GET', '/api/tariffs');
}

export async function getTariff(tariffId: number): Promise<Tariff> {
  return await apiRequest<Tariff>('GET', `/api/tariffs/${tariffId}`);
}

// === ПОДПИСКИ ===

export async function purchaseSubscription(data: {
  user_id: string;
  tariff_id: number;
  card_cryptogram?: string;
  name?: string;
  email?: string;
  transaction_id?: string;
  card_token?: string;  // ✅ Токен карты для рекуррентных платежей
}): Promise<ApiResponse> {
  return await apiRequest<ApiResponse>('POST', '/api/subscription/purchase', data);
}

export async function getSubscriptionStatus(userId: string): Promise<SubscriptionStatus> {
  return await apiRequest<SubscriptionStatus>('GET', `/api/subscription/status/${userId}`);
}

export async function pauseSubscription(userId: string): Promise<ApiResponse> {
  return await apiRequest<ApiResponse>('POST', '/api/subscription/pause', {
    user_id: userId
  });
}

export interface CancelSubscriptionData {
  cardNumber: string;
  expiryDate: string;
  cvv: string;
  cardholderName: string;
}

export async function cancelSubscription(userId: string, cardData: CancelSubscriptionData): Promise<ApiResponse> {
  // Разбиваем номер карты на первые 6 и последние 4 цифры
  const cardNumber = cardData.cardNumber.replace(/\D/g, '');
  const card_first_six = cardNumber.slice(0, 6);
  const card_last_four = cardNumber.slice(-4);
  
  return await apiRequest<ApiResponse>('POST', '/api/subscription/cancel', {
    user_id: userId,
    card_first_six: card_first_six,
    card_last_four: card_last_four,
    account_id: cardData.cardholderName, // ID аккаунта передаётся в cardholderName
    reason: 'Отмена подписки по запросу пользователя'
  });
}

// === ПОДДЕРЖКА ===

export async function contactSupport(userId: string, subject: string, message: string): Promise<ApiResponse> {
  return await apiRequest<ApiResponse>('POST', '/api/support/contact', {
    user_id: userId,
    subject: subject,
    message: message
  });
}

// === УТИЛИТЫ ===

export function handleApiError(error: any, defaultMessage: string = 'Произошла ошибка'): string {
  if (error?.message) {
    return error.message;
  }
  return defaultMessage;
}