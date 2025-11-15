import React, { useState, useEffect } from 'react'
import './PaymentScreen.css'
import { purchaseSubscription, getTariffs, getSubscriptionStatus } from '../utils/api'
import { showAlert, hapticFeedback, getUserId } from '../utils/telegram'

// Типы для CloudPayments
declare global {
  interface Window {
    cp: any;
  }
}

interface PaymentScreenProps {
  selectedPlan: number
  currentUserId: string
}

const PaymentScreen = ({ selectedPlan, currentUserId }: PaymentScreenProps) => {
  const [isProcessing, setIsProcessing] = useState(false)
  const [isTermsChecked, setIsTermsChecked] = useState(false)
  const [isSubscriptionChecked, setIsSubscriptionChecked] = useState(false)
  const [tariffs, setTariffs] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [currentSubscription, setCurrentSubscription] = useState<any>(null)

  // Загружаем тарифы и информацию о подписке при монтировании компонента
  useEffect(() => {
    const loadData = async () => {
      try {
        // Загружаем тарифы
        console.log('Loading tariffs...')
        const tariffsResponse = await getTariffs()
        console.log('Tariffs response:', tariffsResponse)
        
        // Backend возвращает массив тарифов напрямую
        if (Array.isArray(tariffsResponse)) {
          setTariffs(tariffsResponse)
          console.log('Tariffs loaded:', tariffsResponse)
        } else {
          console.error('Unexpected tariffs response format:', tariffsResponse)
        }

        // Загружаем информацию о текущей подписке
        try {
          const subscriptionResponse = await getSubscriptionStatus(currentUserId)
          if (subscriptionResponse.success) {
            setCurrentSubscription(subscriptionResponse)
          }
        } catch (error) {
          console.log('No current subscription found')
        }
      } catch (error) {
        console.error('Error loading data:', error)
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [currentUserId])

  // Загружаем CloudPayments виджет
  useEffect(() => {
    const script = document.createElement('script')
    script.src = 'https://widget.cloudpayments.ru/bundles/cloudpayments.js'
    script.async = true
    document.head.appendChild(script)

    return () => {
      document.head.removeChild(script)
    }
  }, [])

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

  const handlePayment = () => {
    console.log('=== Payment Debug Info ===')
    console.log('selectedPlan:', selectedPlan)
    console.log('tariffs loaded:', tariffs)
    console.log('isLoading:', isLoading)
    console.log('currentSubscription:', currentSubscription)
    
    if (!isTermsChecked || !isSubscriptionChecked) {
      showAlert('Необходимо согласиться с условиями')
      return
    }

    // Получаем тариф по индексу или по названию
    let selectedTariff = null
    
    if (isLoading || tariffs.length === 0) {
      showAlert('Тарифы еще загружаются, попробуйте снова')
      return
    }
    
    // Сопоставляем индекс selectedPlan с названиями тарифов
    const planNames = ['Демо', 'Эко', 'Фулл', 'Суточный', 'Эксклюзив', 'Комбо']
    const selectedPlanName = planNames[selectedPlan]
    
    if (selectedPlanName) {
      selectedTariff = tariffs.find(t => t.name === selectedPlanName)
    }
    
    if (!selectedTariff) {
      console.error('Available tariffs:', tariffs)
      console.error('Selected plan index:', selectedPlan)
      console.error('Selected plan name:', selectedPlanName)
      showAlert(`Тариф "${selectedPlanName}" не найден на сервере`)
      return
    }
    
    console.log('Selected tariff:', selectedTariff)

    setIsProcessing(true)
    hapticFeedback('medium')

    // Открываем CloudPayments виджет
    const widget = new window.cp.CloudPayments()
    
    widget.pay('charge', {
      publicId: 'pk_844cb2c7d4788dc1a506e33a68b18',
      description: selectedTariff.name,  // ✅ Только название тарифа, без суммы
      amount: selectedTariff.price,
      currency: 'RUB',
      invoiceId: `instarding_${currentUserId}_${selectedTariff.id}_${Date.now()}`,
      accountId: currentUserId,
      email: '',  // Убираем email, чтобы не показывалась галочка
      requireEmail: false,  // Отключаем требование email
      requireRecurrent: true,  // ✅ Включаем рекуррентные платежи (токенизация карты)
      skin: 'mini',
      data: {
        service: 'InstardingBot',
        tariff_id: selectedTariff.id,
        user_id: currentUserId
      }
    }, {
      onSuccess: async function(options: any) {
        // Успешная оплата
        console.log('✅ Payment success!')
        console.log('Options:', options)
        console.log('All keys:', Object.keys(options))
        
        // CloudPayments не возвращает токен в onSuccess
        // Токен приходит в webhook на бэкенд
        // Поэтому просто активируем подписку, а токен получим из webhook
        
        try {
          const response = await purchaseSubscription({
            user_id: currentUserId,
            tariff_id: selectedTariff.id,
            transaction_id: undefined,  // Токен придёт в webhook
            card_token: undefined,  // Токен придёт в webhook
            card_cryptogram: undefined,
            name: undefined,
            email: undefined
          })

          if (response.success) {
            hapticFeedback('success')
            showAlert(`Успешно! ${response.message}`)
            
            // Возвращаемся к предыдущему экрану через 2 секунды
            setTimeout(() => {
              window.history.back()
            }, 2000)
          } else {
            throw new Error(response.message)
          }
        } catch (error: any) {
          console.error('Payment processing error:', error)
          hapticFeedback('error')
          showAlert(`Ошибка обработки платежа: ${error.message || error}`)
        } finally {
          setIsProcessing(false)
        }
      },
      onFail: function(reason: string, options: any) {
        // Ошибка оплаты
        console.error('Payment failed:', reason, options)
        hapticFeedback('error')
        showAlert(`Ошибка оплаты: ${reason}`)
        setIsProcessing(false)
      },
      onComplete: function(paymentResult: any, options: any) {
        // Завершение процесса (вызывается всегда)
        console.log('Payment completed:', paymentResult, options)
        setIsProcessing(false)
      }
    })
  }

  // Функция для получения текста согласия в зависимости от тарифа
  const getSubscriptionAgreementText = () => {
    const plan = plans[selectedPlan]
    
    switch (plan.name) {
      case 'Демо':
        return 'Согласен на подключение тарифа “Эксклюзив” и автоматическую оплату 999 рублей каждые 10 дней по истечении пробного периода через 1 сутки. При условии неуспешной попытки подключения тарифа “Эксклюзив” активируется тариф “Фулл” стоимостью 349р за 4 дня использования. При условии неуспешной попытки подключения тарифа “Фулл” активируется тариф “Эко” стоимостью 249р за 2 дня.\n'
      
      case 'Эко':
        return  <>Согласен с <a style={{color: "lightblue"}} href="https://cloud.mail.ru/public/mVrN/mSryioEAz
">правилами предоставления доступа к сервису по подписке </a> с использованием автоплатежа и уведомлен о подключении платной подписки</>
      
      case 'Эксклюзив':
        return   <>Согласен с <a style={{color: "lightblue"}} href="https://cloud.mail.ru/public/mVrN/mSryioEAz
">правилами предоставления доступа к сервису по подписке </a> с использованием автоплатежа и уведомлен о подключении платной подписки</>
      
      case 'Фулл':
        return  <>Согласен с <a style={{color: "lightblue"}} href="https://cloud.mail.ru/public/mVrN/mSryioEAz
">правилами предоставления доступа к сервису по подписке </a> с использованием автоплатежа и уведомлен о подключении платной подписки</>

      case 'Суточный':
      case 'Комбо 5':
      case 'Комбо 10':
        return null // Для этих тарифов второе согласие не показываем
      
      default:
        return null
    }
  }

  return (
    <div className="payment-screen">
      {/* Логотип */}


      {/* Кнопка назад */}

      {/* Заголовок */}
      <div className="payment-header" style={{marginTop: "30px"}}>
        <h1 className="payment-title">Тариф "{plans[selectedPlan].name}"</h1>
        <p className="payment-subtitle">{plans[selectedPlan].subtitle}</p>
        <div className="selected-plan-info">
          <div className="plan-price">{plans[selectedPlan].price}</div>
          <div className="plan-duration">{plans[selectedPlan].duration}</div>
        </div>
      </div>

      {/* Преимущества выбранного тарифа */}
      <div className="features-section">
        <h3 className="features-title">Преимущества тарифа:</h3>
        <div className="features-list">
          {plans[selectedPlan].features.map((feature, index) => (
            <div key={index} className="feature-item">
              <img src="/item.png" width={65} alt="Feature" className="feature-icon" />
              <span className="feature-text">{feature}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Кнопка оплаты */}
      <button 
        className={`payment-button ${isProcessing ? 'processing' : ''}`}
        onClick={handlePayment}
        disabled={isProcessing || !isTermsChecked || (!!getSubscriptionAgreementText() && !isSubscriptionChecked)}
      >
        {isProcessing ? 'Обработка...' : `Оплатить ${plans[selectedPlan].price}`}
      </button>

      {/* Согласие */}
      <div className="agreements-section">
        <div className="agreement-item">
          <input 
            type="checkbox" 
            id="terms-checkbox"
            className="agreement-checkbox"
            checked={isTermsChecked}
            onChange={(e) => setIsTermsChecked(e.target.checked)}
          />
          <label htmlFor="terms-checkbox" className="agreement-text">
            Согласен с <a href="https://cloud.mail.ru/public/kP2w/xQdsRRRUZ" target="_blank" rel="noopener noreferrer" className="agreement-link">договором оферты</a>, <a href="https://cloud.mail.ru/public/kK5B/feVCZ7G8W" target="_blank" rel="noopener noreferrer" className="agreement-link">политикой обработки персональных данных</a>, <a href="https://cloud.mail.ru/public/mVrN/mSryioEAz" target="_blank" rel="noopener noreferrer" className="agreement-link">правилами предоставления услуг</a> по политике, <a href="https://cloud.mail.ru/public/qax1/DC3pJLe9i" target="_blank" rel="noopener noreferrer" className="agreement-link">оферте, рекурентные платежи</a> и <a href="https://cloud.mail.ru/public/n4vr/3AR6LW1oj" target="_blank" rel="noopener noreferrer" className="agreement-link">договором сохранения учетных данных</a>.
          </label>
        </div>
        
        {/* Показываем второе согласие только для тарифов с автоподпиской */}
        {getSubscriptionAgreementText() && (
          <div className="agreement-item">
            <input 
              type="checkbox" 
              id="subscription-checkbox"
              className="agreement-checkbox"
              checked={isSubscriptionChecked}
              onChange={(e) => setIsSubscriptionChecked(e.target.checked)}
            />
            <label htmlFor="subscription-checkbox" className="agreement-text subscription-agreement">
              {getSubscriptionAgreementText()}
            </label>
          </div>
        )}
      </div>

      {/* Платежные системы */}
      <div className="payment-systems">
        <div className="payment-logo mir">МИР</div>
        <div className="payment-logo visa">VISA</div>
        <div className="payment-logo mastercard">MasterCard</div>
        <div className="payment-provider">CloudPayments</div>
      </div>
    </div>
  )
}

export default PaymentScreen 