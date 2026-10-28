# 🤖 Telegram Account Shop Bot

Telegram бот для автоматической продажи цифровых аккаунтов (в формате **Tdata**) с поддержкой нескольких платёжных систем.

---

## ✨ Возможности

- 🛒 Автоматическая продажа аккаунтов через Telegram
- 💳 Три способа оплаты:
  - **CryptoBot** — оплата в рублях через @CryptoBot
  - **Tonkeeper** — оплата в TON через deeplink
  - **Trust Wallet** — ручная оплата в TON с комментарием
- 🔄 Автоматическая проверка транзакций через TON Center API
- 📦 Автоматическая доставка архива (zip/rar) после оплаты
- 👤 Панель администратора для добавления и удаления аккаунтов
- 🗄️ SQLite база данных для хранения данных

---

## 📋 Требования

- Python 3.10+
- Аккаунт [@CryptoBot](https://t.me/CryptoBot) и API токен
- TON кошелёк (Tonkeeper или Trust Wallet)
- API ключ [TON Center](https://toncenter.com/)

---

## ⚙️ Установка

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/bababuy1992-cmyk/TG-bot.git
cd TG-bot
```

### 2. Создайте виртуальное окружение

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

### 3. Установите зависимости

```bash
pip install -r requirements.txt
```

### 4. Настройте конфигурацию

Откройте файл `config.py` и заполните все значения:

```python
TELEGRAM_TOKEN   = "ВАШ_TELEGRAM_BOT_TOKEN"     # от @BotFather
CRYPTOPAY_TOKEN  = "ВАШ_CRYPTOPAY_TOKEN"          # от @CryptoBot → Crypto Pay
ADMIN_ID         = 123456789                       # ваш Telegram user ID
WALLET_ADDRESS   = "ВАШ_TON_АДРЕС"               # ваш TON кошелёк
TONCENTER_API_KEY = "ВАШ_TONCENTER_КЛЮЧ"          # от toncenter.com
PRICE_TARGET_RUB = 15                              # цена в рублях
```

#### Где получить токены:

| Параметр | Где получить |
|---|---|
| `TELEGRAM_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `CRYPTOPAY_TOKEN` | [@CryptoBot](https://t.me/CryptoBot) → Crypto Pay → My Apps |
| `ADMIN_ID` | [@userinfobot](https://t.me/userinfobot) |
| `WALLET_ADDRESS` | Ваш TON кошелёк в Tonkeeper или Trust Wallet |
| `TONCENTER_API_KEY` | [toncenter.com/api](https://toncenter.com/api/v2/) → Get API Key |

---

## 🚀 Запуск

### Windows

```bat
run_bot.bat
```

### Linux / Mac

```bash
python main.py
```

---

## 👨‍💼 Команды администратора

| Команда | Описание |
|---|---|
| `/add` | Добавить новый аккаунт (страна → отлёжка → архив) |
| `/delete` | Показать список аккаунтов для удаления |

---

## 📁 Структура проекта

```
TG-bot/
├── main.py            # Основной файл бота
├── config.py          # Конфигурация (токены, цены)
├── database.py        # Работа с SQLite базой данных
├── crypto_payment.py  # Интеграция с CryptoBot
├── ton_payment.py     # Интеграция с TON Center
├── requirements.txt   # Зависимости Python
├── run_bot.bat        # Скрипт запуска (Windows)
└── accounts/          # Папка для хранения архивов аккаунтов
```

---

## ⚠️ Важно

- Все аккаунты предоставляются в формате **Tdata**
- Не публикуйте `config.py` с реальными токенами в открытый репозиторий
- Загружайте архивы только через команду `/add` в боте

---

## 📄 Лицензия

MIT License
