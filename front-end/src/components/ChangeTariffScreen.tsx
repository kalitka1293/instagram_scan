import { useState } from 'react'
import './ChangeTariffScreen.css'

interface ChangeTariffScreenProps {
  onSubscribe?: (planIndex: number) => void
  currentUserId: string
}

const ChangeTariffScreen = ({ onSubscribe }: ChangeTariffScreenProps) => {
  const [selectedPlan, setSelectedPlan] = useState(0) // Индекс выбранного плана

  // Только тарифы для смены: Суточный, Эксклюзив, Фулл
  const plans = [
    {
      name: 'Суточный',
      price: '499₽',
      duration: '24 часа',
      subtitle: '24 часа — и ты знаешь ВСЁ.',
      features: [
        'Максимум данных за 1 день! — полный отчёт по активности: лайки, комментарии, подписки',
        'Подписной рейтинг - Анализ самых значимых подписок',
        'Только факты — без воды — вся аналитика в одном месте'
      ],
      originalIndex: 2 // Индекс в оригинальном массиве планов
    },
    {
      name: 'Эксклюзив',
      price: '999₽',
      duration: '10 дней',
      subtitle: 'Максимальный функционал сервиса на 10 дней!',
      features: [
        'Полный контроль над ситуацией — 10 дней безлимитного доступа к данным',
        'Раскрой, с кем профиль взаимодействует скрытно',
        'Твой личный помощник — анализируй поведение цели день за днём'
      ],
      originalIndex: 3 // Индекс в оригинальном массиве планов
    },
    {
      name: 'Фулл',
      price: '349₽',
      duration: '4 дня',
      subtitle: 'Всё, что скрыто - теперь в твоих руках',
      features: [
        'Гибкий срок – Оптимальный баланс цены и времени доступа',
        'Всё, что скрыто — подписки, лайки, комментарии — полный расклад',
        'Идеально для анализа — 4 дня — достаточно, чтобы всё найти'
      ],
      originalIndex: 4 // Индекс в оригинальном массиве планов
    }
  ]

  const handlePlanSelect = (index: number) => {
    setSelectedPlan(index)
  }

  const handleSubscribe = () => {
    // Передаём оригинальный индекс плана для корректной обработки
    onSubscribe?.(plans[selectedPlan].originalIndex)
  }

  return (
    <div className="change-tariff-screen">
      {/* Логотип */}

      
      <div className="change-tariff-header">
        <div className="hero-section">
          <div className="hero-illustration">
            <img src="/girl.png" alt="Girl with phone" className="hero-image" />
          </div>
          
          <div className="hero-content">
            <h2 className="hero-title">Изменить тариф</h2>
            <h3 className="current-plan-title">{plans[selectedPlan].name}</h3>
            <p className="hero-subtitle">{plans[selectedPlan].subtitle}</p>
          </div>
        </div>
      </div>

      <div className="tariff-plans">
        {plans.map((plan, index) => (
          <div 
            key={index} 
            className={`tariff-plan ${selectedPlan === index ? 'selected' : ''}`}
            onClick={() => handlePlanSelect(index)}
          >
            <div className="plan-header">
              <h3 className="plan-name">{plan.name}</h3>
              <div className="plan-pricing">
                <span className="plan-price">{plan.price}</span>
                <span className="plan-duration">{plan.duration}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="features-list">
        {plans[selectedPlan].features.map((feature, index) => (
          <div key={index} className="feature-item">
            <img src="/item.png" alt="Feature" className="feature-icon" />
            <div className="feature-content">
              <span className="feature-text">{feature}</span>
            </div>
          </div>
        ))}
      </div>

      <button className="change-tariff-btn" onClick={handleSubscribe}>
        Изменить на {plans[selectedPlan].price}
      </button>
    </div>
  )
}

export default ChangeTariffScreen















