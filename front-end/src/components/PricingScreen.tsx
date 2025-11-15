import { useState } from 'react'
import './PricingScreen.css'

interface PricingScreenProps {
  onSubscribe?: (planIndex: number) => void
  currentUserId: string
}

const PricingScreen = ({ onSubscribe }: PricingScreenProps) => {
  const [selectedPlan, setSelectedPlan] = useState(0) // Индекс выбранного плана

  const plans = [
    {
      name: 'Демо',
      price: '19₽',
      duration: 'Далее 999₽/10 дн.',
      subtitle: 'Попробуй весь функционал сервиса всего за 19₽ на 24 часа!',
      features: [
        'Всё самое важное за копейки — полный доступ к сервису',
        'Кто в тени? — раскрой скрытых поклонников и тайные связи',
        'Быстро, дёшево, эффективно — идеально, если нужно проверить срочно!'
      ]
    },
    {
      name: 'Эко',
      price: '249₽',
      duration: '2 дня',
      subtitle: '2 дня мощной аналитики дешевле, чем обед в кафе!',
      features: [
        'Лайки и комментарии – Увидишь, кто активнее всего взаимодействует',
        'Экономия времени – Вся ключевая информация за 2 дня',
        'Скрытые наблюдатели – Кто следит за аккаунтом, не подписываясь'
      ]
    },
    {
      name: 'Суточный',
      price: '499₽',
      duration: '24 часа',
      subtitle: '24 часа — и ты знаешь ВСЁ.',
      features: [
        'Максимум данных за 1 день! — полный отчёт по активности: лайки, комментарии, подписки',
        'Подписной рейтинг - Анализ самых значимых подписок',
        'Только факты — без воды — вся аналитика в одном месте'
      ]
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
      ]
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
      ]
    },
    {
      name: 'Комбо 5',
      price: '699₽',
      duration: '5 запросов',
      subtitle: '5 точных ответов на самые важные вопросы',
      features: [
        '5 точных запросов – Получи ответы на самые важные вопросы',
        'Без подписки – Оплати один раз и используй когда угодно',
        'Любые данные – Лайки, комментарии, подписки – что угодно за раз'
      ]
    },
    {
      name: 'Комбо 10',
      price: '1099₽',
      duration: '10 запросов',
      subtitle: '10 запросов = абсолютная ясность. Бери и узнавай ВСЁ!',
      features: [
        'В 2 раза мощнее! — 10 запросов = полная картина происходящего',
        'Расширенная статистика - Максимум данных за минимум запросов',
        'Экономия 300₽ при двойном объёме!'
      ]
    }
  ]

  const handlePlanSelect = (index: number) => {
    setSelectedPlan(index)
  }

  return (
    <div className="pricing-screen">
      {/* Логотип */}

      <div className="pricing-header">
        <div className="hero-section">
          <div className="hero-illustration">
            <img src="/girl.png" alt="Girl with phone" className="hero-image" />
          </div>
          
          <div className="hero-content">
            <h2 className="hero-title">{plans[selectedPlan].name}</h2>
            <p className="hero-subtitle">{plans[selectedPlan].subtitle}</p>
          </div>
        </div>
      </div>

      <div className="pricing-plans">
        {plans.map((plan, index) => (
          <div 
            key={index} 
            className={`pricing-plan ${selectedPlan === index ? 'selected' : ''}`}
            onClick={() => handlePlanSelect(index)}
          >
            <div className="plan-header">
              <h3 className="plan-name">
                {plan.name}
              </h3>
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

      <button className="subscribe-btn" onClick={() => onSubscribe?.(selectedPlan)}>
        Подписаться за {plans[selectedPlan].price}
      </button>
    </div>
  )
}

export default PricingScreen 