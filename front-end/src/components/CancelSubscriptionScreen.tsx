import { useState } from 'react'
import './CancelSubscriptionScreen.css'
import { cancelSubscription } from '../utils/api'

interface CancelSubscriptionScreenProps {
  onBack: () => void
  currentUserId: string
}

const CancelSubscriptionScreen = ({ onBack, currentUserId }: CancelSubscriptionScreenProps) => {
  const [firstSixDigits, setFirstSixDigits] = useState('')
  const [lastFourDigits, setLastFourDigits] = useState('')
  const [accountId, setAccountId] = useState('')
  const [reason, setReason] = useState('')
  const [showSuccess, setShowSuccess] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    // Валидация
    if (!firstSixDigits || firstSixDigits.length !== 6) {
      setError('Введите первые 6 цифр карты')
      return
    }
    if (!lastFourDigits || lastFourDigits.length !== 4) {
      setError('Введите последние 4 цифры карты')
      return
    }
    if (!accountId) {
      setError('Введите ID аккаунта')
      return
    }
    if (!reason) {
      setError('Укажите причину отмены')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const result = await cancelSubscription(currentUserId, {
        cardNumber: firstSixDigits + lastFourDigits,
        expiryDate: '',
        cvv: '',
        cardholderName: accountId
      })

      if (result.success) {
        setShowSuccess(true)
      } else {
        setError(result.message || 'Не удалось отменить подписку')
      }
    } catch (err: any) {
      console.error('Ошибка при отмене подписки:', err)
      setError(err.message || 'Произошла ошибка при отмене подписки')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCloseSuccess = () => {
    setShowSuccess(false)
    onBack() // Возвращаемся на предыдущую страницу
  }

  return (
    <div className="cancel-subscription-screen">
      {/* Логотип */}

      <div className="cancel-content">
        {/* Поле первых 6 цифр */}
        <div className="form-group">
          <label className="form-label">Введите первые 6 цифр номера карты:</label>
          <input
            type="text"
            value={firstSixDigits}
            onChange={(e) => setFirstSixDigits(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            className="form-input"
            maxLength={6}
          />
        </div>

        {/* Поле последних 4 цифр */}
        <div className="form-group">
          <label className="form-label">Введите последние 4 цифры номера карты:</label>
          <input
            type="text"
            value={lastFourDigits}
            onChange={(e) => setLastFourDigits(e.target.value.replace(/\D/g, '').slice(0, 4))}
            placeholder="0000"
            className="form-input"
            maxLength={4}
          />
        </div>

        {/* Поле ID аккаунта */}
        <div className="form-group">
          <label className="form-label">Введите ID аккаунта*</label>
          <input
            type="text"
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            placeholder="id"
            className="form-input"
          />
        </div>

        {/* Поле причины */}
        <div className="form-group">
          <label className="form-label">Укажите причину, по которой Вы хотите отменить подписку:</label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Причина"
            className="form-textarea"
            rows={3}
          />
        </div>

        {/* Сообщение об ошибке */}
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

        {/* Кнопка отмены */}
        <button 
          className="cancel-button" 
          onClick={handleSubmit}
          disabled={isLoading}
          style={{
            opacity: isLoading ? 0.6 : 1,
            cursor: isLoading ? 'not-allowed' : 'pointer'
          }}
        >
          {isLoading ? 'Отмена подписки...' : 'Отменить подписку'}
        </button>

        {/* Подсказка */}
        <div className="info-text">
          *Ваш ID Аккаунта находится во вкладке "Информация" (крайняя правая).
        </div>
      </div>

      {/* Поп-ап успешной отправки */}
      {showSuccess && (
        <div className="success-modal">
          <div className="success-content">
            <h2 className="success-title">Заявка на отмену подписки отправлена!</h2>
            <button className="success-button" onClick={handleCloseSuccess}>
              Окей
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default CancelSubscriptionScreen