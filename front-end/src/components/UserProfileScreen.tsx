import { useState, useEffect } from 'react'
import './UserProfileScreen.css'
import { checkInstagramProfile, getProfileFollowers, getProxyImageUrl, type InstagramProfile, type UserActivities } from '../utils/api'
import { showAlert } from '../utils/telegram'
import Activities from './Activities'

interface UserProfileScreenProps {
  profile: string
  onSubscribe: (planIndex?: number) => void
  onPricingClick?: () => void
  currentUserId: string
}

interface MetricItem {
  title: string
  value: string
}

interface MetricsData {
  popular: MetricItem[]
  likes: MetricItem[]
  subscriptions: MetricItem[]
  comments: MetricItem[]
  posts: MetricItem[]
  watchers: MetricItem[]
  chats: MetricItem[]
}

// Используем типы из API
type ProfileData = InstagramProfile & {
  analytics_data?: MetricsData
  user_activities?: UserActivities
}

const UserProfileScreen = ({ profile, onSubscribe, onPricingClick, currentUserId }: UserProfileScreenProps) => {
  const [activeTab, setActiveTab] = useState('popular')
  const [currentTabIndex, setCurrentTabIndex] = useState(0)
  const [metricsData, setMetricsData] = useState<MetricsData>({} as MetricsData)
  const [profileData, setProfileData] = useState<ProfileData | null>(null)
  const [userActivities, setUserActivities] = useState<UserActivities | null>(null)
  const [commentsData, setCommentsData] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [showPosts, setShowPosts] = useState(true)
  const [followersLoading, setFollowersLoading] = useState<boolean>(true)
  const [followersStatus, setFollowersStatus] = useState<string>('pending')
  const [hasActiveSubscription, setHasActiveSubscription] = useState<boolean>(false)

  // Функция для форматирования чисел
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M'
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K'
    }
    return num.toString()
  }

  // Загружаем полные данные профиля с бэкенда
  useEffect(() => {
    const loadProfileData = async () => {
      if (!profile) return
      
      setIsLoading(true)
      setFollowersLoading(true)
      
      try {
        // Получаем базовые данные профиля (мгновенно)
        const response = await checkInstagramProfile(profile, currentUserId)
        
        if (response.success && response.profile) {
          setProfileData(response.profile)
          setMetricsData(response.profile.analytics_data || getDefaultMetricsData())
          setUserActivities(response.user_activities || null)
          setCommentsData(response.comments_data || [])
          setHasActiveSubscription(response.has_active_subscription || false)
        } else {
          setMetricsData(getDefaultMetricsData())
          setUserActivities(null)
          setCommentsData([])
          setHasActiveSubscription(false)
        }
      } catch (error) {
        setMetricsData(getDefaultMetricsData())
        setUserActivities(null)
        showAlert('Не удалось загрузить данные профиля')
      } finally {
        setIsLoading(false)
      }
      
      // Запускаем опрос подписчиков
      pollFollowers()
    }

    const pollFollowers = async () => {
      try {
        const followersResponse = await getProfileFollowers(profile)
        
        if (followersResponse.status === "completed") {
          // Подписчики готовы, обновляем активности
          setFollowersStatus("completed")
          setFollowersLoading(false)
          
          if (followersResponse.mutual_followers) {
            // Генерируем активности на основе взаимных подписчиков
            // Перемешиваем массив для разнообразия
            const shuffledFollowers = [...followersResponse.mutual_followers].sort(() => Math.random() - 0.5);
            
            const newActivities: UserActivities = {
              recent_likes: shuffledFollowers.slice(0, 10).map(f => ({
                username: f.username,
                full_name: f.full_name || f.username,
                profile_pic_url: getProxyImageUrl(f.profile_pic_url || '/default-avatar.png'),
                action: "оценил (а) ваш пост",
                status: Math.random() > 0.5 ? "Новый!" : "Сейчас",
                timestamp: new Date().toISOString()
              })),
              recent_follows: shuffledFollowers.slice(0, 8).map(f => ({
                username: f.username,
                full_name: f.full_name || f.username,
                profile_pic_url: getProxyImageUrl(f.profile_pic_url || '/default-avatar.png'),
                action: "подписался на вас",
                status: Math.random() > 0.7 ? "Новый!" : "5 мин назад",
                timestamp: new Date().toISOString()
              })),
              recent_comments: shuffledFollowers.slice(18, 26).map(f => ({
                username: f.username,
                full_name: f.full_name || f.username,
                profile_pic_url: getProxyImageUrl(f.profile_pic_url || '/default-avatar.png'),
                action: "прокомментировал ваш пост",
                status: Math.random() > 0.6 ? "Сейчас" : "10 мин назад",
                timestamp: new Date().toISOString()
              })),
              recent_messages: shuffledFollowers.slice(26, 30).map(f => ({
                username: f.username,
                full_name: f.full_name || f.username,
                profile_pic_url: getProxyImageUrl(f.profile_pic_url || '/default-avatar.png'),
                action: "отправил сообщение",
                status: Math.random() > 0.8 ? "Новый!" : "30 мин назад",
                timestamp: new Date().toISOString()
              }))
            }
            setUserActivities(newActivities)
          }
        } else if (followersResponse.status === "pending" || followersResponse.status === "processing") {
          // Продолжаем опрос через 3 секунды
          setFollowersStatus(followersResponse.status)
          setTimeout(pollFollowers, 3000)
        } else {
          // Ошибка
          setFollowersStatus("failed")
          setFollowersLoading(false)
        }
      } catch (error) {
        console.error("Ошибка при получении подписчиков:", error)
        setFollowersStatus("failed")
        setFollowersLoading(false)
      }
    }

    loadProfileData()
  }, [profile, currentUserId])

  // Обновляем комментарии при переходе на вкладку "Комментарии"
  useEffect(() => {
    const loadCommentsForTab = async () => {
      if (activeTab === 'comments' && profile && commentsData.length === 0) {
        try {
          const response = await checkInstagramProfile(profile, currentUserId)
          if (response.success && response.comments_data) {
            setCommentsData(response.comments_data)
          }
        } catch (error) {
          console.error('Ошибка загрузки комментариев:', error)
        }
      }
    }
    
    loadCommentsForTab()
  }, [activeTab, profile, currentUserId])

  // Базовые метрики только с нужной информацией
  const getDefaultMetricsData = (): MetricsData => ({
    popular: [
      { title: 'Репосты', value: profileData ? formatNumber(Math.floor(profileData.posts_count * 0.15)) : '89' },
      { title: 'Охват', value: profileData ? formatNumber(Math.floor(profileData.followers_count * 1.2)) : '12,456' },
      { title: 'Просмотры', value: profileData ? formatNumber(Math.floor(profileData.followers_count * 0.8)) : '24,891' },
      { title: 'Лайки', value: profileData ? formatNumber(Math.floor(profileData.posts_count * profileData.followers_count * 0.03)) : '2,847' },
      { title: 'Комментарии', value: profileData ? formatNumber(Math.floor(profileData.posts_count * profileData.followers_count * 0.005)) : '1,203' },
      { title: 'Истории', value: profileData ? formatNumber(Math.floor(profileData.posts_count * 2.1)) : '234' },
      { title: 'Рилс', value: profileData ? formatNumber(Math.floor(profileData.posts_count * 0.6)) : '89' },
      { title: 'Групповые чаты', value: profileData ? formatNumber(Math.floor(profileData.following_count * 0.02)) : '5' },
    ],
    likes: [],
    subscriptions: [],
    comments: [],
    posts: [],
    watchers: [],
    chats: []
  })

  // Обновленные вкладки
  const allTabs = [
    { id: 'popular', label: 'Популярное' },
    { id: 'likes', label: 'Лайки' },
    { id: 'comments', label: 'Комментарии' },
    { id: 'connections', label: 'Подписки' },
    { id: 'chats', label: 'Активные переписки' },
    { id: 'watchers', label: 'Наблюдатели' },
    { id: 'posts', label: 'Посты и Reels' }
  ]

  // Вычисляем какие 3 вкладки показывать
  const getVisibleTabs = () => {
    const totalTabs = allTabs.length
    
    if (totalTabs <= 3) {
      return allTabs
    }
    
    let startIndex = currentTabIndex - 1
    
    // Если активная вкладка в начале списка
    if (currentTabIndex === 0) {
      startIndex = 0
    }
    // Если активная вкладка в конце списка  
    else if (currentTabIndex === totalTabs - 1) {
      startIndex = totalTabs - 3
    }
    
    return allTabs.slice(startIndex, startIndex + 3)
  }

  const handlePrevTab = () => {
    const prevIndex = currentTabIndex > 0 ? currentTabIndex - 1 : allTabs.length - 1
    setCurrentTabIndex(prevIndex)
    setActiveTab(allTabs[prevIndex].id)
  }

  const handleNextTab = () => {
    const nextIndex = currentTabIndex < allTabs.length - 1 ? currentTabIndex + 1 : 0
    setCurrentTabIndex(nextIndex)
    setActiveTab(allTabs[nextIndex].id)
  }



  return (
    <div className="user-profile-screen">
      {/* Логотип */}


      {/* Карточка профиля */}
      <div className="profile-card">
        <div className="profile-header">
          <div className="profile-avatar">
            <img 
              src={getProxyImageUrl(profileData?.profile_pic_url || 'https://cp14.nevsepic.com.ua/213/21259/1385297849-05.jpg')} 
              alt="Profile" 
              className="avatar-image" 
            />
            {profileData?.is_verified && (
              <div className="verified-badge">✓</div>
            )}
          </div>
          <div className="profile-info">
            <h2 className="profile-name">
              {profileData?.full_name || profileData?.username || profile}
            </h2>
            <p className="profile-username">@{profileData?.username || profile}</p>
            {profileData?.biography && (
              <p className="profile-bio">{profileData.biography}</p>
            )}
            {profileData?.external_url && (
              <a href={profileData.external_url} className="profile-link" target="_blank" rel="noopener noreferrer">
                🔗 {profileData.external_url}
              </a>
            )}
            <div className="profile-badges">
              {profileData?.is_business && (
                <span className="business-badge">🏢 Бизнес аккаунт</span>
              )}
              {profileData?.is_private && (
                <span className="private-badge">🔒 Приватный аккаунт</span>
              )}
            </div>
          </div>
        </div>
        
                  <div className="profile-stats">
          <div className="stat-item">
            <div className="stat-label">Посты</div>
            <div className="stat-value">{formatNumber(profileData?.posts_count || 0)}</div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Подписчики</div>
            <div className="stat-value">{formatNumber(profileData?.followers_count || 0)}</div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Подписки</div>
            <div className="stat-value">{formatNumber(profileData?.following_count || 0)}</div>
          </div>
        </div>

      </div>



      {/* Вкладки метрик */}
      <div className="metrics-tabs-container">
        <div className="metrics-navigation">
          <button className="nav-arrow nav-arrow-left" onClick={handlePrevTab}>
            <img src="/arrow.png" alt="Previous" className="arrow-icon arrow-left" />
          </button>
          
          <div className="metrics-tabs">
            {getVisibleTabs().map((tab) => (
              <button 
                key={tab.id}
                className={`metrics-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => {
                  const tabIndex = allTabs.findIndex(t => t.id === tab.id)
                  setCurrentTabIndex(tabIndex)
                  setActiveTab(tab.id)
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
          
          <button className="nav-arrow nav-arrow-right" onClick={handleNextTab}>
            <img src="/arrow.png" alt="Next" className="arrow-icon arrow-right" />
          </button>
        </div>
        
        <div className="tab-indicators">
          {allTabs.map((_, index) => (
            <div 
              key={index}
              className={`tab-indicator ${index === currentTabIndex ? 'active' : ''}`}
              onClick={() => {
                setCurrentTabIndex(index)
                setActiveTab(allTabs[index].id)
              }}
            />
          ))}
        </div>
      </div>

      {/* Сетка статистик - только для популярного */}
      {activeTab === 'popular' && (
        <div className="statistics-grid">
          {isLoading ? (
            // Показываем загрузку
            <>
              {[...Array(8)].map((_, index) => (
                <div key={index} className="stat-card loading">
                  <div className="stat-title">Загрузка...</div>
                  <div className="stat-number">—</div>
                </div>
              ))}
            </>
          ) : (
            // Показываем данные
            metricsData.popular?.map((stat: MetricItem, index: number) => (
              <div key={index} className="stat-card">
                <div className="stat-title">{stat.title}</div>
                <div className="stat-number">{stat.value}</div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Последние посты - только для вкладки "Популярное" */}
      {activeTab === 'popular' && profileData?.posts_data && profileData.posts_data.length > 0 && (
        <div className="recent-posts-section">
          <div className="section-header">
            <h3>📸 Последние посты</h3>
            <button 
              className="toggle-posts-btn" 
              onClick={() => setShowPosts(!showPosts)}
            >
              {showPosts ? 'Скрыть' : 'Показать'}
            </button>
          </div>
          
          {showPosts && (
            <div className="posts-grid">
              {profileData.posts_data.slice(0, 6).map((post, index) => (
                <div key={index} className="post-card">
                  <div className="post-thumbnail">
                    {post.thumbnail_url ? (
                      <img 
                        src={getProxyImageUrl(post.thumbnail_url)} 
                        alt="Post thumbnail" 
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                          const placeholder = target.nextSibling as HTMLElement;
                          if (placeholder) {
                            placeholder.style.display = 'flex';
                          }
                        }}
                      />
                    ) : null}
                    <div 
                      className="post-placeholder"
                      style={{ display: post.thumbnail_url ? 'none' : 'flex' }}
                    >
                      {post.is_video ? '🎥' : '🖼'}
                    </div>
                    {post.is_video && <div className="video-indicator">▶️</div>}
                  </div>
                  

                  
                  {/* Убрали только кнопку "Открыть в Instagram" */}
                </div>
              ))}
            </div>
          )}


        </div>
      )}

      {/* Активности пользователя - только для соответствующих вкладок */}
      {activeTab !== 'popular' && (
        <Activities 
          userActivities={userActivities} 
          onPricingClick={onPricingClick}
          isLoading={followersLoading}
          loadingStatus={followersStatus}
          profileData={profileData}
          hasPaidSubscription={hasActiveSubscription}
          activeTab={activeTab}
          commentsData={commentsData}
        />
      )}


    </div>
  )
}

export default UserProfileScreen