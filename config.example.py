# Скопируйте этот файл в config.py и заполните реальными значениями:
# cp config.example.py config.py

TELEGRAM_TOKEN    = "ВАШ_TELEGRAM_BOT_TOKEN"      # от @BotFather
CRYPTOPAY_TOKEN   = "ВАШ_CRYPTOPAY_TOKEN"           # от @CryptoBot -> Crypto Pay
ADMIN_ID          = 123456789                        # ваш Telegram ID (узнать: @userinfobot)
WALLET_ADDRESS    = "ВАШ_TON_АДРЕС"                # ваш TON кошелёк
TONCENTER_API_KEY = "ВАШ_TONCENTER_API_KEY"         # от toncenter.com

# Цена (чистыми, без комиссии)
PRICE_TARGET_RUB = 15

# CryptoBot берёт ~1.5% комиссии
CRYPTO_BOT_COMMISSION = 0.015
PRICE_CRYPTOBOT = round(PRICE_TARGET_RUB / (1 - CRYPTO_BOT_COMMISSION), 2)

# TON: gas платит покупатель, оставляем без наценки
PRICE_TON_RUB = PRICE_TARGET_RUB
