import React from 'react';
import './Activities.css';
import { getProxyImageUrl } from '../utils/api';

interface UserActivity {
  username: string;
  full_name: string;
  profile_pic_url?: string;
  action: string;
  status: string;
  timestamp?: string;
  likes_count?: number;
}

interface Comment {
  id: string;
  text: string;
  username: string;
  full_name: string;
  profile_pic_url?: string;
  post_url?: string;
  post_image_url?: string;
}

interface UserActivities {
  recent_likes: UserActivity[];
  recent_follows: UserActivity[];
  recent_comments: UserActivity[];
  recent_messages: UserActivity[];
}

interface ActivitiesProps {
  userActivities: UserActivities | null;
  onPricingClick?: () => void;
  isLoading?: boolean;
  loadingStatus?: string;
  profileData?: any;
  hasPaidSubscription?: boolean;
  activeTab?: string;
  commentsData?: Comment[];
}

interface ActivitySectionProps {
  title: string;
  icon: string;
  data: UserActivity[];
  limit?: number;
  onPricingClick?: () => void;
  isLoading?: boolean;
  loadingStatus?: string;
  isBlurred?: boolean;
  showLoadMore?: boolean;
  hasPaidSubscription?: boolean;  // ✅ Добавили проп
}

const Activities: React.FC<ActivitiesProps> = ({ 
  userActivities, 
  onPricingClick, 
  isLoading = false, 
  loadingStatus = "pending", 
  profileData = null,
  hasPaidSubscription = false,
  activeTab = "likes",
  commentsData = []
}) => {
  const handlePremiumClick = () => {
    if (onPricingClick) {
      onPricingClick();
    }
  };

  // Генерируем фиктивные данные для разделов с уникальными картинками
  const generateFakeUsers = (count: number, action: string, includeStats = false, sectionSeed = 0) => {
    const fakeUsers = [];
    const names = ['alex_photo', 'maria_style', 'john_travel', 'anna_art', 'mike_fitness', 'lisa_food', 'david_music', 'kate_fashion'];
    const fullNames = ['Александр Петров', 'Мария Стиль', 'Джон Тревел', 'Анна Арт', 'Майк Фитнес', 'Лиза Фуд', 'Дэвид Мьюзик', 'Кейт Фешн'];
    
    // Ключ для localStorage
    const storageKey = profileData?.username ? `active_profiles_${profileData.username}` : 'active_profiles_default';
    
    for (let i = 0; i < count; i++) {
      const randomIndex = Math.floor(Math.random() * names.length);
      const username = names[randomIndex] + Math.floor(Math.random() * 100);
      
      let likesCount;
      if (includeStats) {
        // Проверяем localStorage только для фейковых данных
        const stored = localStorage.getItem(`${storageKey}_${username}`);
        if (stored) {
          likesCount = parseInt(stored);
        } else {
          // Генерируем новое значение в медиане от 0 до количества постов
          const postsCount = profileData?.posts_count || 10;
          likesCount = Math.floor(Math.random() * (postsCount + 1)); // +1 чтобы включить само количество постов
          // Сохраняем в localStorage
          localStorage.setItem(`${storageKey}_${username}`, likesCount.toString());
        }
      } else {
        likesCount = Math.floor(Math.random() * 50) + 5;
      }
      
      // Создаем уникальный seed для каждого раздела и пользователя
      const uniqueImageSeed = sectionSeed * 100 + i + 1;
        
      fakeUsers.push({
        username: username,
        full_name: fullNames[randomIndex],
        profile_pic_url: `https://picsum.photos/100/100?random=${uniqueImageSeed}`,
        action: action,
        status: Math.random() > 0.6 ? "Новый!" : "Сейчас",
        timestamp: new Date().toISOString(),
        likes_count: likesCount
      });
    }
    return fakeUsers;
  };

  const ActivitySection: React.FC<ActivitySectionProps> = ({ 
    title, 
    icon, 
    data, 
    limit = 4, 
    onPricingClick, 
    isLoading, 
    loadingStatus,
    isBlurred = false,
    showLoadMore = false,
    hasPaidSubscription = false  // ✅ Добавили параметр
  }) => {
    // Показываем состояние загрузки
    if (isLoading) {
      return (
        <div className="activity-section">
          <h3 className="activity-title">
            <span className="activity-icon">{icon}</span>
            {title}
          </h3>
          <div className="activity-list">
            {[...Array(4)].map((_, index) => (
              <div key={index} className="activity-item loading-item">
                <div className="loading-content">
                  <div className="loading-spinner">⏳</div>
                  <div className="loading-text">
                    {loadingStatus === "processing" ? "Идет анализ..." : "Ожидание анализа..."}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    const visibleItems = data ? data.slice(0, limit) : [];

    return (
      <div className="activity-section">
        <h3 className="activity-title">
          <span className="activity-icon">{icon}</span>
          {title}
        </h3>
        <div className="activity-wrapper">
          <div className={`activity-list ${isBlurred ? 'blurred-section' : ''}`}>
            {visibleItems.length === 0 && isBlurred ? (
              <div className="no-activity">
                <span className="no-activity-icon">🔍</span>
                <span className="no-activity-text">Не удалось обнаружить</span>
              </div>
            ) : visibleItems.length === 0 ? (
              <div className="no-activity">
                <span className="no-activity-icon">🔍</span>
                <span className="no-activity-text">Активность не обнаружена</span>
              </div>
            ) : (
              visibleItems.map((item, index) => (
              <div key={index} className={`activity-item list-item ${isBlurred ? 'blurred-item' : ''}`}>
                <div className="activity-header">
                  <img 
                    src={getProxyImageUrl(item.profile_pic_url || '/default-avatar.png')} 
                    alt={item.username}
                    className="activity-avatar"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                      const fallback = target.nextSibling as HTMLElement;
                      if (fallback) {
                        fallback.style.display = 'flex';
                      }
                    }}
                  />
                  <div className="activity-avatar-fallback">👤</div>
                </div>
                <div className="activity-content">
                  <div className="activity-username">@{item.username}</div>
                  <div className="activity-action">
                    {item.action}
                    {item.likes_count && ` (${item.likes_count} лайков)`}
                  </div>
                </div>
              </div>
            ))
            )}
          </div>
          
          {isBlurred && (
            <div className="unlock-controls">
              {hasPaidSubscription ? (
                // Если есть подписка, но данных нет - показываем уведомление
                <div className="data-unavailable-notice">
                  <span className="notice-icon">ℹ️</span>
                  <span className="notice-text">Не удалось спарсить данные</span>
                </div>
              ) : (
                // Если нет подписки - показываем кнопку активации
                <>
                  <div className="lock-icon">🔒</div>
                  <button className="locked-button" onClick={onPricingClick || handlePremiumClick}>
                    Активируйте тариф всего за 19 руб.
                  </button>
                </>
              )}
            </div>
          )}
          
          {showLoadMore && !isBlurred && (
            <button className="load-more-btn" onClick={onPricingClick || handlePremiumClick}>
              Загрузить ещё
            </button>
          )}
        </div>
      </div>
    );
  };

  // Компонент для отображения комментариев
  const CommentsSection: React.FC<{ comments: Comment[], isBlurred: boolean }> = ({ comments, isBlurred }) => {
    // Создаем массив из 5 элементов: реальные комментарии + заблюренные плейсхолдеры
    const allComments = [];
    
    // Добавляем реальные комментарии (максимум 2)
    const realComments = comments.slice(0, 2);
    realComments.forEach((comment, index) => {
      allComments.push({
        ...comment,
        isBlurred: false,
        key: `real-${index}`
      });
    });
    
    // Добавляем заблюренные плейсхолдеры до 5 штук
    const blurredCount = 5 - realComments.length;
    for (let i = 0; i < blurredCount; i++) {
      allComments.push({
        id: `blur-${i}`,
        username: 'кто-то написал',
        text: 'что-то написал',
        profile_pic_url: `https://picsum.photos/100/100?random=${i + 100}`, // Рандомные аватарки
        post_image_url: `https://picsum.photos/200/200?random=${i + 200}`, // Рандомные посты
        post_url: '#',
        isBlurred: true,
        key: `blur-${i}`
      });
    }
    
    // Перемешиваем для чередования блюр/не блюр
    const shuffled = [...allComments];
    // Простое перемешивание: ставим заблюренные через один
    const mixed = [];
    let realIndex = 0;
    let blurIndex = realComments.length;
    
    for (let i = 0; i < 5; i++) {
      if (i % 2 === 0 && realIndex < realComments.length) {
        mixed.push(shuffled[realIndex++]);
      } else if (blurIndex < shuffled.length) {
        mixed.push(shuffled[blurIndex++]);
      } else if (realIndex < realComments.length) {
        mixed.push(shuffled[realIndex++]);
      }
    }
    
    return (
      <div className="comments-section">
        <h3 className="activity-title">
          <span className="activity-icon">💬</span>
          Полученные комментарии
        </h3>
        
        <div className="comments-grid">
          {mixed.map((comment, index) => (
            <div key={comment.key} className={`comment-card ${comment.isBlurred ? 'comment-card-blurred' : ''}`}>
              <div className="comment-main">
                <div className="comment-left">
                  <div className="comment-header">
                    <img 
                      src={getProxyImageUrl(comment.profile_pic_url || '/default-avatar.png')} 
                      alt={comment.username}
                      className={`comment-avatar-small ${comment.isBlurred ? 'blurred-avatar' : ''}`}
                    />
                    <div className={`comment-username ${comment.isBlurred ? '' : ''}`}>
                      {comment.isBlurred ? comment.username : `@${comment.username}`}
                    </div>
                  </div>
                  
                  <div className={`comment-text-small ${comment.isBlurred ? '' : ''}`}>
                    {comment.isBlurred ? comment.text : comment.text}
                  </div>
                </div>
                
                <div className="comment-right">
                  <div className="comment-post-small">
                    <img 
                      src={getProxyImageUrl(comment.post_image_url || '/item.png')} 
                      alt="Post" 
                      className={`comment-post-image-small ${comment.isBlurred ? 'blurred-image' : ''}`} 
                    />
                  </div>
                  {/* Убрали кнопку "Открыть пост" */}
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <button className="load-more-btn" onClick={onPricingClick || handlePremiumClick}>
          Загрузить ещё
        </button>
      </div>
    );
  };

  // Данные для новых разделов - используем реальных взаимных подписчиков для активных профилей
  // Каждый раздел получает уникальный seed для генерации разных картинок
  const activeLikesData = userActivities?.recent_likes && userActivities.recent_likes.length > 0 
    ? userActivities.recent_likes.slice(0, 5) 
    : [];  // ✅ Пустой массив вместо фейковых данных
  
  // Для "Последние лайки" используем другую часть данных ТОЛЬКО если есть реальные данные
  const likesData = userActivities?.recent_likes && userActivities.recent_likes.length > 5
    ? userActivities.recent_likes.slice(5, 9) // Берем следующие 4 элемента
    : [];  // ✅ Пустой массив вместо фейковых данных
  // Отладка: проверяем что приходит в userActivities
  console.log('🔍 userActivities:', userActivities);
  console.log('📊 recent_follows:', userActivities?.recent_follows);
  console.log('📊 recent_follows length:', userActivities?.recent_follows?.length);

  // Для "Подписки" используем первую часть recent_follows ТОЛЬКО если есть реальные данные
  const subscriptionsData = (userActivities?.recent_follows && userActivities.recent_follows.length > 0)
    ? userActivities.recent_follows.slice(0, 3) 
    : [];  // ✅ Пустой массив вместо фейковых данных
  
  // Для "Подписчики" используем вторую часть recent_follows ТОЛЬКО если есть данные
  const followersData = (userActivities?.recent_follows && userActivities.recent_follows.length > 3)
    ? userActivities.recent_follows.slice(3, 6)
    : [];  // ✅ Пустой массив вместо фейковых данных
  
  console.log('🔍 subscriptionsData:', subscriptionsData);
  console.log('🔍 followersData:', followersData);
  const chatsData = generateFakeUsers(4, "активная переписка", false, 5);
  const watchersData = generateFakeUsers(4, "наблюдает за профилем", false, 6);
  const postsData = generateFakeUsers(4, "оценил(-а) пост", false, 7);

  // Определяем какой раздел показывать
  const renderActiveTabContent = () => {
    switch (activeTab) {
      case 'likes':
        return (
          <>
            {/* Активные профили - всегда открыты */}
            <ActivitySection 
              title="Активные профили"
              icon="🔥"
              data={activeLikesData}
              limit={5}
              onPricingClick={onPricingClick}
              isLoading={isLoading}
              loadingStatus={loadingStatus}
              showLoadMore={true}
              hasPaidSubscription={hasPaidSubscription}
            />
            
            {/* Последние лайки - заблокированы без подписки */}
            <ActivitySection 
              title="Последние лайки"
              icon="💕"
              data={likesData}
              limit={4}
              onPricingClick={onPricingClick}
              isLoading={isLoading}
              loadingStatus={loadingStatus}
              isBlurred={!hasPaidSubscription}
              hasPaidSubscription={hasPaidSubscription}
            />
          </>
        );
      
      case 'comments':
        return (
          <>
            <CommentsSection 
              comments={commentsData || []}
              isBlurred={!hasPaidSubscription}
            />
            
            {/* Блок отправленных комментариев */}
            <div className="tab-notice" style={{ marginTop: '20px' }}>
              В данном блоке показаны комментарии, которые цель отправил(-а) под постами других пользователей.
            </div>
            <ActivitySection 
              title="Отправленные комментарии"
              icon="💬"
              data={generateFakeUsers(6, "комментировал(-а) пост", false, 8)}
              limit={4}
              onPricingClick={onPricingClick}
              isLoading={isLoading}
              loadingStatus={loadingStatus}
              isBlurred={!hasPaidSubscription}
              hasPaidSubscription={hasPaidSubscription}
            />
          </>
        );
      
      case 'connections':
        return (
          <>
            {/* Подписки */}
            <ActivitySection 
              title="Последние подписки"
              icon="👥"
              data={subscriptionsData}
              limit={4}
              onPricingClick={onPricingClick}
              isLoading={isLoading}
              loadingStatus={loadingStatus}
              isBlurred={!hasPaidSubscription}
              hasPaidSubscription={hasPaidSubscription}
            />
            
            {/* Последние, кто отписался */}
            <ActivitySection 
              title="Последние, кто отписался"
              icon="👋"
              data={generateFakeUsers(6, "отписался(-лась)", false, 9)}
              limit={4}
              onPricingClick={onPricingClick}
              isLoading={isLoading}
              loadingStatus={loadingStatus}
              isBlurred={!hasPaidSubscription}
              hasPaidSubscription={hasPaidSubscription}
            />
            
            {/* Подписчики */}
            <ActivitySection 
              title="Последние кто подписался"
              icon="👤"
              data={followersData}
              limit={4}
              onPricingClick={onPricingClick}
              isLoading={isLoading}
              loadingStatus={loadingStatus}
              isBlurred={!hasPaidSubscription}
              hasPaidSubscription={hasPaidSubscription}
            />
          </>
        );
      
      case 'chats':
        return (
          <>
            <div className="tab-notice">
              В данном блоке показаны профили, с которыми анализируемый аккаунт активнее всего взаимодействует в переписках. Важно: учитываются в том числе отправленные Посты и Reels.
            </div>
            <ActivitySection 
              title="Активные переписки"
              icon="💬"
              data={chatsData}
              limit={4}
              onPricingClick={onPricingClick}
              isLoading={isLoading}
              loadingStatus={loadingStatus}
              isBlurred={!hasPaidSubscription}
              hasPaidSubscription={hasPaidSubscription}
            />
          </>
        );
      
      case 'watchers':
        return (
          <>
            <div className="tab-notice">
              В данном блоке показаны профили, которые не подписаны на анализируемый аккаунт, но все равно взаимодействуют с его контентом: посещают, лайкают и комментируют.
            </div>
            <ActivitySection 
              title="Наблюдатели"
              icon="👁️"
              data={watchersData}
              limit={4}
              onPricingClick={onPricingClick}
              isLoading={isLoading}
              loadingStatus={loadingStatus}
              isBlurred={!hasPaidSubscription}
              hasPaidSubscription={hasPaidSubscription}
            />
          </>
        );
      
      case 'posts':
        return (
          <>
            <div className="tab-notice">
              В данном блоке показаны последние Посты и Reels, которые цель оценил(-а) или оставил комментарий.
            </div>
            <ActivitySection 
              title="Посты и Reels"
              icon="📸"
              data={postsData}
              limit={4}
              onPricingClick={onPricingClick}
              isLoading={isLoading}
              loadingStatus={loadingStatus}
              isBlurred={!hasPaidSubscription}
              hasPaidSubscription={hasPaidSubscription}
            />
          </>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="activities-container">
      {renderActiveTabContent()}
    </div>
  );
};

export default Activities;


