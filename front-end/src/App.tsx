import { useState, useEffect } from 'react'
import './App.css'
import ProfileCheckScreen from './components/ProfileCheckScreen'
import UserProfileScreen from './components/UserProfileScreen'
import StatsScreen from './components/StatsScreen'
import PricingScreen from './components/PricingScreen'
import InfoScreen from './components/InfoScreen'
import PaymentScreen from './components/PaymentScreen'
import PauseSubscriptionScreen from './components/PauseSubscriptionScreen'
import TariffManagementScreen from './components/TariffManagementScreen'
import CancelSubscriptionScreen from './components/CancelSubscriptionScreen'
import ChangeTariffScreen from './components/ChangeTariffScreen'
import AnalysisProcessScreen from './components/AnalysisProcessScreen'
import BottomNavigation from './components/BottomNavigation'
import { initTelegramWebApp, getUserId, getTelegramUser } from './utils/telegram'
import { loginUser } from './utils/api'
import type { User } from './utils/api'

function App() {
  const [currentScreen, setCurrentScreen] = useState('profile-check')
  const [currentProfile, setCurrentProfile] = useState('')
  const [selectedPlan, setSelectedPlan] = useState(0)
  const [currentUserId, setCurrentUserId] = useState<string>('')
  const [userData, setUserData] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  // Инициализация Telegram WebApp и авторизация пользователя
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Инициализируем Telegram WebApp
        initTelegramWebApp()
        
        // Получаем user_id из Telegram
        const userId = getUserId()
        const telegramUser = getTelegramUser()
        
        console.log('🚀 Инициализация приложения...')
        console.log('👤 Telegram User ID:', userId)
        console.log('👤 Telegram User:', telegramUser)
        
        setCurrentUserId(userId)
        
        // Авторизуемся на бэкенде
        const authResponse = await loginUser(userId)
        
        if (authResponse.success && authResponse.user) {
          setUserData(authResponse.user)
          console.log('✅ Авторизация успешна:', authResponse.user)
        } else {
          console.error('❌ Ошибка авторизации:', authResponse.message)
        }
        
      } catch (error) {
        console.error('❌ Ошибка инициализации:', error)
      } finally {
        setIsLoading(false)
      }
    }

    initializeApp()
  }, [])

  const handleProfileSubmit = (profile: string) => {
    setCurrentProfile(profile)
    setCurrentScreen('user-profile')
  }

  const handleSubscribe = (planIndex?: number) => {
    if (planIndex !== undefined) {
      setSelectedPlan(planIndex)
    }
    setCurrentScreen('payment')
  }

  const handlePauseSubscription = () => {
    setCurrentScreen('pause-subscription')
  }

  const handleBackFromPause = () => {
    setCurrentScreen('info')
  }

  const handleTariffManagement = () => {
    setCurrentScreen('tariff-management')
  }

  const handleCancelSubscription = () => {
    setCurrentScreen('cancel-subscription')
  }

  const handleBackFromCancel = () => {
    setCurrentScreen('tariff-management')
  }

  const handleChangeTariff = () => {
    setCurrentScreen('change-tariff')
  }

  const handleAnalysisProcess = () => {
    setCurrentScreen('analysis-process')
  }

  const handleBackFromAnalysis = () => {
    setCurrentScreen('info')
  }

  const renderScreen = () => {
    if (isLoading) {
      return (
        <div className="loading-screen">

          <h2>🚀 Инициализация...</h2>
          <p>Подключение к Telegram WebApp</p>
        </div>
      )
    }

    switch (currentScreen) {
      case 'profile-check':
        return <ProfileCheckScreen onProfileSubmit={handleProfileSubmit} currentUserId={currentUserId} />
      case 'user-profile':
        return (
          <UserProfileScreen 
            profile={currentProfile} 
            onSubscribe={handleSubscribe}
            onPricingClick={() => setCurrentScreen('pricing')}
            currentUserId={currentUserId}
          />
        )
      case 'stats':
        return <StatsScreen profile={currentProfile} currentUserId={currentUserId} />
      case 'pricing':
        return <PricingScreen onSubscribe={handleSubscribe} currentUserId={currentUserId} />
      case 'info':
        return <InfoScreen onPauseSubscription={handlePauseSubscription} onTariffManagement={handleTariffManagement} onAnalysisProcess={handleAnalysisProcess} userData={userData} currentUserId={currentUserId} />
      case 'payment':
        return <PaymentScreen selectedPlan={selectedPlan} currentUserId={currentUserId} />
      case 'pause-subscription':
        return <PauseSubscriptionScreen onBack={handleBackFromPause} currentUserId={currentUserId} />
      case 'tariff-management':
        return <TariffManagementScreen onCancelSubscription={handleCancelSubscription} onChangeTariff={handleChangeTariff} currentUserId={currentUserId} />
      case 'cancel-subscription':
        return <CancelSubscriptionScreen onBack={handleBackFromCancel} currentUserId={currentUserId} />
      case 'change-tariff':
        return <ChangeTariffScreen onSubscribe={handleSubscribe} currentUserId={currentUserId} />
      case 'analysis-process':
        return <AnalysisProcessScreen onBack={handleBackFromAnalysis} />
      default:
        return <ProfileCheckScreen onProfileSubmit={handleProfileSubmit} currentUserId={currentUserId} />
    }
  }

  return (
    <div className="app">
      <div className="screen-container">
        {renderScreen()}
      </div>
      <BottomNavigation 
        currentScreen={currentScreen} 
        onScreenChange={setCurrentScreen} 
      />
    </div>
  )
}

export default App
