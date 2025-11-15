import './TariffManagementScreen.css'

interface TariffManagementScreenProps {
  onCancelSubscription: () => void
  onChangeTariff: () => void
  currentUserId: string
}

const TariffManagementScreen = ({ onCancelSubscription, onChangeTariff }: TariffManagementScreenProps) => {
  const handleSupport = () => {
    // Здесь будет логика обращения в поддержку
    console.log('Обращение в поддержку')
  }

  return (
    <div className="tariff-management-screen">
      {/* Логотип */}

      {/* Основной контент */}
      <div className="tariff-content">
        <div className="management-text">
          Если вы приняли решение прекратить использование сервиса и аннулировать активную подписку, это можно сделать одним из двух способов, предусмотренных условиями договора оферты и правил пользования.
          <br /><br />
          Вы вправе направить обращение с требованием аннулировать подписку на адрес электронной почты: insidegram@mail.ru. В теме письма необходимо указать: «Отменить подписку». В теле письма следует предоставить данные, необходимые в пункте 7.8 Договора Оферты, необходимые для идентификации пользователя и корректной обработки запроса. Рассмотрение поступивших заявлений осуществляется в течение 24 часов в рабочие дни.
          <br /><br />
          Однако в отдельных случаях срок рассмотрения и исполнения запроса может составлять до 5 рабочих дней. В письме необходимо предоставить сведения, предусмотренные пунктом 7.8 Договора Оферты, необходимые для идентификации пользователя.
          <br /><br />
          Заявка рассматривается в течение 24 часов в рабочие дни, однако полный срок обработки может составлять до 5 рабочих дней.
          <br /><br />
          В соответствии с Правилами Пользования, клиент имеет возможность самостоятельно инициировать процесс аннулирования подписки путём заполнения <span className="application-link" onClick={onCancelSubscription}><strong>заявления</strong></span>, размещённого на официальном ресурсе сервиса. Обращаем Ваше внимание на необходимость корректного указания всех запрашиваемых данных, включая номер платёжной карты, использованной при активации подписки, так как данная информация необходима для правильной регистрации запроса на отключение. При возникновении трудностей с отменой подписки можете обратиться в Службу Поддержки, кратко описав процедуры отключения. При возникновении проблем предоставят подробное описание.
        </div>

        <div className="action-buttons">
          <a style={{textAlign: "center"}} className="action-button support-btn pause-btn" href={"https://t.me/insidegram_support"} onClick={handleSupport}>
            <span className="support-text">Поддержка</span>
          </a>

          <button className="action-button support-btn" onClick={onChangeTariff}>
            Изменить тариф
          </button>

          <button className="action-button restore-btn" onClick={onCancelSubscription}>
            Восстановить покупку
          </button>
          

          

        </div>

      </div>
    </div>
  )
}

export default TariffManagementScreen