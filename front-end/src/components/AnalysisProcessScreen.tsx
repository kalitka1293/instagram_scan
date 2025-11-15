import './AnalysisProcessScreen.css'

interface AnalysisProcessScreenProps {
  onBack?: () => void
}

const AnalysisProcessScreen = ({ onBack }: AnalysisProcessScreenProps) => {
  return (
    <div className="analysis-process-screen">
      {/* Логотип */}

      {/* Кнопка назад */}
      <div className="back-section">
        <button className="back-button" onClick={onBack}>
          ← Назад
        </button>
      </div>

      <div className="analysis-content">
        <div className="analysis-header">
          <h1 className="analysis-title">Как работает анализ в Insidegram</h1>
        </div>

        <div className="analysis-text">
          <p className="analysis-paragraph">
            Наш сервис использует технологии анализа данных в рамках официальных возможностей платформы. Мы собираем и систематизируем открытую информацию, предоставляя вам детализированную аналитику активности профиля.
          </p>

          <p className="analysis-paragraph">
            Мы работаем строго в рамках разрешенных методов, используя только те данные, которые доступны через официальный Instagram API*.
          </p>

          <p className="analysis-paragraph">
            Результаты зависят от настроек приватности профиля и текущих возможностей платформы. Чем больше информации открыто, тем глубже и точнее будет анализ.
          </p>

          <div className="disclaimer">
            * Принадлежит компании Meta, признанной экстремистской и запрещённой на территории РФ
          </div>
        </div>
      </div>
    </div>
  )
}

export default AnalysisProcessScreen
