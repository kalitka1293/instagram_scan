#!/usr/bin/env python3
"""
Скрипт для проверки последнего платежа и настройки рекуррентных платежей
"""
from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()

print("=" * 70)
print("💳 ПРОВЕРКА ПОСЛЕДНЕГО ПЛАТЕЖА И РЕКУРРЕНТНОЙ ПОДПИСКИ")
print("=" * 70)

# Последний платёж
payment = db.query(models.Payment).order_by(models.Payment.id.desc()).first()
if payment:
    print("\n✅ ПОСЛЕДНИЙ ПЛАТЁЖ:")
    print(f"   ID: {payment.id}")
    print(f"   User ID: {payment.user_id}")
    print(f"   Tariff ID: {payment.tariff_id}")
    print(f"   Amount: {payment.amount}₽")
    print(f"   Status: {payment.status}")
    print(f"   Transaction ID: {payment.transaction_id}")
    print(f"   CloudPayments Transaction ID: {payment.cloudpayments_transaction_id}")
    print(f"   💳 Card Token: {payment.card_token or '❌ НЕТ'}")
    print(f"   🔄 Is Recurrent: {payment.is_recurrent}")
    print(f"   Created At: {payment.created_at}")
    print(f"   Paid At: {payment.paid_at}")
else:
    print("\n❌ ПЛАТЕЖЕЙ НЕТ В БД")

print("\n" + "=" * 70)

# Последняя подписка
sub = db.query(models.SubscriptionHistory).order_by(models.SubscriptionHistory.id.desc()).first()
if sub:
    print("\n✅ ПОСЛЕДНЯЯ ПОДПИСКА:")
    print(f"   ID: {sub.id}")
    print(f"   User ID: {sub.user_id}")
    print(f"   Tariff ID: {sub.tariff_id}")
    print(f"   Status: {sub.status}")
    print(f"   🔄 Auto Renewal: {sub.auto_renewal}")
    print(f"   💳 Card Token: {sub.card_token or '❌ НЕТ'}")
    print(f"   ☁️ CloudPayments Subscription ID: {sub.cloudpayments_subscription_id or '❌ НЕТ'}")
    print(f"   📅 Next Payment Date: {sub.next_payment_date or '❌ НЕ УСТАНОВЛЕНА'}")
    print(f"   Start Date: {sub.start_date}")
    print(f"   End Date: {sub.end_date}")
    print(f"   Failed Attempts: {sub.failed_attempts}")
    
    # Проверяем тариф
    tariff = db.query(models.Tariff).filter(models.Tariff.id == sub.tariff_id).first()
    if tariff:
        print(f"   📦 Tariff Name: {tariff.name}")
        print(f"   💰 Tariff Price: {tariff.price}₽")
else:
    print("\n❌ ПОДПИСОК НЕТ В БД")

print("\n" + "=" * 70)

# Проверяем пользователя
if payment:
    user = db.query(models.User).filter(models.User.user_id == payment.user_id).first()
    if user:
        print("\n✅ ПОЛЬЗОВАТЕЛЬ:")
        print(f"   User ID: {user.user_id}")
        print(f"   Is Paid: {user.is_paid}")
        print(f"   Current Tariff ID: {user.current_tariff_id}")
        print(f"   Subscription Start: {user.subscription_start}")
        print(f"   Subscription End: {user.subscription_end}")
        print(f"   Remaining Requests: {user.remaining_requests}")

print("\n" + "=" * 70)
print("\n📊 АНАЛИЗ:")

if payment and sub:
    if payment.card_token and sub.card_token:
        print("✅ Токен карты сохранён - рекуррентные платежи ВОЗМОЖНЫ")
    else:
        print("❌ Токен карты НЕ сохранён - рекуррентные платежи НЕ РАБОТАЮТ")
    
    if sub.auto_renewal:
        print("✅ Auto Renewal включён")
    else:
        print("⚠️ Auto Renewal выключен - автоплатежи не будут")
    
    if sub.cloudpayments_subscription_id:
        print(f"✅ CloudPayments подписка создана: {sub.cloudpayments_subscription_id}")
    else:
        print("❌ CloudPayments подписка НЕ создана - автоплатежи не будут")
    
    if sub.next_payment_date:
        print(f"✅ Следующий платёж запланирован на: {sub.next_payment_date}")
        
        # Проверяем, когда будет следующий платёж
        now = datetime.now()
        if sub.next_payment_date > now:
            delta = sub.next_payment_date - now
            hours = delta.total_seconds() / 3600
            if hours < 24:
                print(f"   ⏰ Через {hours:.1f} часов")
            else:
                days = hours / 24
                print(f"   ⏰ Через {days:.1f} дней")
        else:
            print(f"   ⚠️ Дата уже прошла! Платёж должен был произойти.")
    else:
        print("❌ Дата следующего платежа НЕ установлена")

print("\n" + "=" * 70)
print("\n🎯 ИТОГ:")

if (payment and payment.card_token and 
    sub and sub.auto_renewal and 
    sub.cloudpayments_subscription_id and 
    sub.next_payment_date):
    print("✅ ВСЁ НАСТРОЕНО ПРАВИЛЬНО!")
    print("   Рекуррентные платежи будут работать автоматически.")
    print(f"   Следующее списание: {sub.next_payment_date}")
else:
    print("❌ РЕКУРРЕНТНЫЕ ПЛАТЕЖИ НЕ НАСТРОЕНЫ!")
    print("\nЧто отсутствует:")
    if not payment or not payment.card_token:
        print("   - Токен карты не сохранён")
    if not sub or not sub.auto_renewal:
        print("   - Auto Renewal не включён")
    if not sub or not sub.cloudpayments_subscription_id:
        print("   - CloudPayments подписка не создана")
    if not sub or not sub.next_payment_date:
        print("   - Дата следующего платежа не установлена")

print("\n" + "=" * 70)

db.close()




