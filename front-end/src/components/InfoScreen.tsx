import './InfoScreen.css'

interface InfoScreenProps {
  onPauseSubscription?: () => void
  onTariffManagement?: () => void
  onAnalysisProcess?: () => void
  userData?: any
  currentUserId?: string
}

const InfoScreen = ({ onPauseSubscription, onTariffManagement, onAnalysisProcess, currentUserId }: InfoScreenProps) => {
  const menuItems = [
    { text: 'Политика обработки данных', url: 'https://cloud.mail.ru/public/kK5B/feVCZ7G8W' },
    { text: 'Тарифы', url: 'https://cloud.mail.ru/public/6N1g/xtZwAfQi2' },
    { text: 'Предоставление услуг', url: 'https://cloud.mail.ru/public/mVrN/mSryioEAz' },
    { text: 'Рекуррентные платежи', url: 'https://cloud.mail.ru/public/qax1/DC3pJLe9i' },
    { text: 'Договор оферты', url: 'https://cloud.mail.ru/public/kP2w/xQdsRRRUZ' },
    { text: 'Сохранение учётных данных', url: 'https://cloud.mail.ru/public/n4vr/3AR6LW1oj' },
    { text: 'Обработка данных', url: 'https://cloud.mail.ru/public/22ok/XHWRMJay5' },
  ]

  return (
    <div className="info-screen">
      {/* Логотип */}

              <div className="menu-list">
          {menuItems.map((item, index) => (
            <a key={index} href={item.url} target="_blank" rel="noopener noreferrer" className="menu-item">
              <span className="menu-text">{item.text}</span>
            </a>
          ))}
        </div>

      {/* Текст о Meta */}
      <div className="meta-disclaimer">
        Meta, признанная судом в РФ экстремистской. Данные меры судебной защиты не ограничивают действий по использованию программных продуктов компании Meta физических и юридических лиц, не принимающих участия в запрещенной законом деятельности
      </div>

      {/* Информация об аккаунте */}
      <div className="account-info">
        {/* ID аккаунта */}
        <div className="account-id-section">
          <div className="account-id-label">Ваш ID аккаунта:</div>
          <div className="account-id-value">{currentUserId || '—'}</div>
        </div>

        {/* Данные ИП */}
        <div className="company-section">
          <div className="company-name">ИП МУКАРРАМОВ РАВШАН МУРОТКУЛОВИЧ</div>
          <div className="company-detail">ОГРНИП: 325547600132430</div>
          <div className="company-detail">ИНН: 540139309266</div>
        </div>

        <div className="support-section">
          <a style={{textAlign: "center"}} className="support-item" href={"https://t.me/insidegram_support"}>Служба поддержки</a>
          <button className="support-item highlighted" onClick={onPauseSubscription}>Приостановить подписку</button>
          <button className="support-item" onClick={onAnalysisProcess}>Как проходит анализ</button>
          <button className="support-item" onClick={onTariffManagement}>Управление</button>
          </div>
      </div>
     
    </div>
  )
}

export default InfoScreen 