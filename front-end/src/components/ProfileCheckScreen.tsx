import { useState } from 'react'
import './ProfileCheckScreen.css'
import { checkInstagramProfile } from '../utils/api'
import { hapticFeedback, showAlert } from '../utils/telegram'

interface ProfileCheckScreenProps {
  onProfileSubmit: (profile: string) => void
  currentUserId: string
}

const ProfileCheckScreen = ({ onProfileSubmit, currentUserId }: ProfileCheckScreenProps) => {
  const [profile, setProfile] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async () => {
    if (!profile.trim()) return
    
    // Вибрация при нажатии кнопки
    hapticFeedback('light')
    
    setIsLoading(true)
    
    try {
      // Реальный запрос к API бэкенда
      const response = await checkInstagramProfile(profile.replace("@", "").trim(), currentUserId)
      
      if (response.success) {
        console.log('✅ Профиль найден:', response.profile)
        hapticFeedback('success')
        onProfileSubmit(profile.replace("@", "").trim())
      } else {
        hapticFeedback('error')
        showAlert(response.message || 'Не удалось найти профиль')
      }
    } catch (error) {
      console.error('❌ Ошибка при проверке профиля:', error)
      hapticFeedback('error')
      
      // Извлекаем сообщение об ошибке
      let errorMessage = 'Ошибка подключения к серверу'
      
      if (error instanceof Error) {
        const message = error.message
        
        // Проверяем специфичные ошибки
        if (message.includes('Profile not found') || message.includes('Профиль не найден')) {
          const username = message.split(':')[1]?.trim() || profile.trim()
          errorMessage = `Профиль @${username} не найден`
        } else if (message.includes('404')) {
          errorMessage = `Профиль @${profile.trim()} не найден`
        } else if (message.includes('422')) {
          errorMessage = 'Некорректные данные профиля'
        } else if (message.includes('500')) {
          errorMessage = 'Ошибка сервера, попробуйте позже'
        } else {
          errorMessage = message
        }
      }
      
      showAlert(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit()
    }
  }

  return (
    <div className="profile-check-screen">

      <div className="content">
        <h1 className="title">Проверим профиль ?</h1>
        <p className="subtitle">
          Введи никнейм пользователя для анализа активности
        </p>
        
        <div className="input-container">
          <input
            type="text"
            className="profile-input"
            placeholder="@username"
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
          />
        </div>
        
        <button
          className="check-button"
          onClick={handleSubmit}
          disabled={!profile.trim() || isLoading}
        >
          {isLoading ? '🔍 Анализируем...' : '🔍 Запустить анализ'}
        </button>
      </div>
    </div>
  )
}

export default ProfileCheckScreen 