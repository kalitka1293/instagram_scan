import { useState } from 'react'
import './PauseSubscriptionScreen.css'
import { pauseSubscription } from '../utils/api'

interface PauseSubscriptionScreenProps {
  onBack: () => void
  currentUserId: string
}

const PauseSubscriptionScreen = ({ onBack, currentUserId }: PauseSubscriptionScreenProps) => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handlePauseSubscription = async () => {
    if (!currentUserId) {
      setError('Ошибка: пользователь не авторизован')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const result = await pauseSubscription(currentUserId)
      
      if (result.success) {
        setSuccess(true)
        // Возвращаемся назад через 2 секунды
        setTimeout(() => {
          onBack()
        }, 2000)
      } else {
        setError(result.message || 'Не удалось приостановить подписку')
      }
    } catch (err: any) {
      console.error('Ошибка при приостановке подписки:', err)
      setError(err.message || 'Произошла ошибка при приостановке подписки')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="pause-screen">
      {/* Логотип */}

      <div className="pause-content">
        {!success ? (
          <>
            <div className="pause-message">
              Если вы временно не планируете пользоваться преимуществами подписки, вы можете её приостановить, а мы сохраним все оплаченные дни.
            </div>

            {error && (
              <div className="error-message" style={{
                background: 'rgba(255, 59, 48, 0.1)',
                border: '1px solid rgba(255, 59, 48, 0.3)',
                borderRadius: '12px',
                padding: '12px 16px',
                marginBottom: '16px',
                color: '#ff3b30',
                fontSize: '14px',
                textAlign: 'center'
              }}>
                {error}
              </div>
            )}

            <button 
              className="pause-button" 
              onClick={handlePauseSubscription}
              disabled={isLoading}
              style={{
                opacity: isLoading ? 0.6 : 1,
                cursor: isLoading ? 'not-allowed' : 'pointer'
              }}
            >
              {isLoading ? 'Приостановка...' : 'Приостановить подписку'}
            </button>

            <div className="pause-details">
              Подробнее о том, как работает услуга приостановки подписке можно узнать в <a href="https://cloud.mail.ru/public/kP2w/xQdsRRRUZ" target="_blank" rel="noopener noreferrer" className="detail-link">Публичной Оферте</a> и <a href="https://cloud.mail.ru/public/6N1g/xtZwAfQi2" target="_blank" rel="noopener noreferrer" className="detail-link">Тарифах</a>.
              <br /><br />
              В соответствии с <a href="https://cloud.mail.ru/public/kP2w/xQdsRRRUZ" target="_blank" rel="noopener noreferrer" className="detail-link">Публичной Офертой</a>, функциональная возможность приостановки подписки производится 1 раз сроком на 7 календарных дней, после чего любой из выбранного ранее <a href="https://cloud.mail.ru/public/6N1g/xtZwAfQi2" target="_blank" rel="noopener noreferrer" className="detail-link">тарифов</a> снова становится необходимым к оплате.
            </div>
          </>
        ) : (
          <div className="success-message">
            <div className="success-icon">✅</div>
            <h3>Подписка приостановлена!</h3>
            <p>
              Подписка успешно приостановлена на 7 дней.
              <br />
              Через 7 дней подписка автоматически возобновится.
            </p>
            <div style={{ 
              fontSize: '14px', 
              marginTop: '16px', 
              opacity: 0.9,
              fontWeight: 500 
            }}>
              Возврат к профилю...
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default PauseSubscriptionScreen