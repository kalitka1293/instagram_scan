/**
 * Утилиты для работы с Telegram WebApp
 */

// Типы для Telegram WebApp
interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    user?: TelegramUser;
    chat?: any;
    start_param?: string;
  };
  expand(): void;
  setHeaderColor(color: string): void;
  MainButton: {
    text: string;
    show(): void;
    hide(): void;
    setText(text: string): void;
    onClick(callback: () => void): void;
  };
  HapticFeedback?: {
    impactOccurred(style: 'light' | 'medium' | 'heavy'): void;
    notificationOccurred(type: 'error' | 'success' | 'warning'): void;
    selectionChanged(): void;
  };
  showAlert(message: string): void;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

export interface UserData {
  id: string;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium: boolean;
}

// Получение данных пользователя из Telegram WebApp
export function getTelegramUser(): UserData {
  if (window.Telegram && window.Telegram.WebApp) {
    const webApp = window.Telegram.WebApp;
    const user = webApp.initDataUnsafe?.user;
    
    if (user) {
      return {
        id: user.id.toString(),
        first_name: user.first_name,
        last_name: user.last_name,
        username: user.username,
        language_code: user.language_code,
        is_premium: user.is_premium || false
      };
    }
  }
  
  // Fallback для разработки (когда приложение запущено не в Telegram)
  return {
    id: "dev_user_" + Math.random().toString(36).substr(2, 9),
    first_name: "Test",
    last_name: "User",
    username: "testuser",
    language_code: "ru",
    is_premium: false
  };
}

// Получение user_id для API
export function getUserId(): string {
  const user = getTelegramUser();
  return user.id;
}

// Инициализация Telegram WebApp
export function initTelegramWebApp(): boolean {
  if (window.Telegram && window.Telegram.WebApp) {
    const webApp = window.Telegram.WebApp;
    
    // Расширяем WebApp на весь экран
    webApp.expand();
    
    // Настраиваем тему
    webApp.setHeaderColor('#FF5E7D');
    
    // Скрываем главную кнопку по умолчанию
    webApp.MainButton.hide();
    
    console.log('🤖 Telegram WebApp инициализирован');
    console.log('👤 Пользователь:', getTelegramUser());
    
    return true;
  }
  
  console.log('⚠️ Telegram WebApp не найден, используем режим разработки');
  return false;
}

// Показать главную кнопку Telegram
export function showMainButton(text: string, onClick: () => void): void {
  if (window.Telegram && window.Telegram.WebApp) {
    const webApp = window.Telegram.WebApp;
    webApp.MainButton.setText(text);
    webApp.MainButton.show();
    webApp.MainButton.onClick(onClick);
  }
}

// Скрыть главную кнопку Telegram
export function hideMainButton(): void {
  if (window.Telegram && window.Telegram.WebApp) {
    const webApp = window.Telegram.WebApp;
    webApp.MainButton.hide();
  }
}

// Показать уведомление в Telegram
export function showAlert(message: string): void {
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.showAlert(message);
  } else {
    alert(message);
  }
}

// Вибрация (если поддерживается)
export function hapticFeedback(type: 'light' | 'medium' | 'heavy' | 'success' | 'error' | 'warning' = 'light'): void {
  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
    if (type === 'success' || type === 'error' || type === 'warning') {
      window.Telegram.WebApp.HapticFeedback.notificationOccurred(type);
    } else {
      window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
    }
  }
}