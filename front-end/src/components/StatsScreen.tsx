import { useState, useEffect } from 'react'
import './StatsScreen.css'
import { getProfileStats } from '../utils/api'
import { showAlert } from '../utils/telegram'

interface StatsScreenProps {
  profile: string
  currentUserId: string
}

const StatsScreen = ({ profile }: StatsScreenProps) => {
  const [activeTab, setActiveTab] = useState('activity')
  const [statsData, setStatsData] = useState<any>({})
  const [isLoading, setIsLoading] = useState<boolean>(true)

  // Загружаем статистику с бэкенда
  useEffect(() => {
    const loadStats = async () => {
      if (!profile) return
      
      setIsLoading(true)
      try {
        const response = await getProfileStats(profile)
        
        if (response.success && response.data) {
          setStatsData(response.data)
          console.log('✅ Статистика загружена:', response.data)
        } else {
          // Fallback к моковым данным
          setStatsData(getMockStats())
          console.log('⚠️ Используем моковые данные статистики')
        }
      } catch (error) {
        console.error('❌ Ошибка загрузки статистики:', error)
        setStatsData(getMockStats())
        showAlert('Не удалось загрузить статистику')
      } finally {
        setIsLoading(false)
      }
    }

    loadStats()
  }, [profile])

  const getMockStats = () => ({
    activity: {
      interactions: 245,
      reactions: 89,
      comments: 156,
      mentions: 67
    },
    engagement: {
      likes: 1205,
      shares: 89,
      saves: 134,
      reach: 3456
    },
    audience: {
      followers: 1234,
      following: 456,
      growth: 15,
      retention: 85
    }
  })

  const renderStats = () => {
    if (isLoading) {
      return (
        <div className="loading-stats">
          <div className="stat-block loading">
            <span className="stat-value">—</span>
            <span className="stat-name">Загрузка...</span>
          </div>
          <div className="stat-block loading">
            <span className="stat-value">—</span>
            <span className="stat-name">Загрузка...</span>
          </div>
          <div className="stat-block loading">
            <span className="stat-value">—</span>
            <span className="stat-name">Загрузка...</span>
          </div>
        </div>
      )
    }

    const stats = statsData[activeTab] || getMockStats()[activeTab as keyof ReturnType<typeof getMockStats>]
    return Object.entries(stats).map(([key, value], index) => (
      <div key={index} className="stat-block">
        <span className="stat-value">{String(value)}</span>
        <span className="stat-name">{key}</span>
      </div>
    ))
  }

  return (
    <div className="stats-screen">
      {/* Логотип */}

      <div className="profile-header">
        <h1 className="profile-name">Статистика для {profile}</h1>
      </div>

      <div className="tabs-container">
        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'activity' ? 'active' : ''}`}
            onClick={() => setActiveTab('activity')}
          >
            Активность
          </button>
          <button 
            className={`tab ${activeTab === 'engagement' ? 'active' : ''}`}
            onClick={() => setActiveTab('engagement')}
          >
            Вовлечение
          </button>
          <button 
            className={`tab ${activeTab === 'audience' ? 'active' : ''}`}
            onClick={() => setActiveTab('audience')}
          >
            Аудитория
          </button>
        </div>
      </div>

      <div className="stats-card">
        <h2 className="card-title">
          {activeTab === 'activity' && 'Анализ активности'}
          {activeTab === 'engagement' && 'Показатели вовлечения'}
          {activeTab === 'audience' && 'Аудитория'}
        </h2>
        <div className="stats-grid">
          {renderStats()}
        </div>
      </div>
    </div>
  )
}

export default StatsScreen 