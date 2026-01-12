Выводы по генерации:

Бот справился хорошо
Но 
1) он не написал как запускать бд
2) Он не аккуратно обрабатывал статусы в бд
3) Создавал повторный платёж если пришло неизвестное уведомление о платеже
4) сделал request_id строкой и числом
5) Не зарегистрировал вебхуки

Поправить
1) FSM изменить на redis в продакшене
2) Заменить pooling на telegram webhook

## ✅ PROMPT ДЛЯ CURSOR (ОБНОВЛЁННЫЙ)

**ROLE**
Ты — опытный Python backend-разработчик, Telegram-боты, aiogram 3, FastAPI, FSM, платежи через ЮKassa, асинхронные API. Пиши чистый production-ready код.

---

## 🎯 Цель проекта

Разработать Telegram-бота для **генерации изображений**, с системой **кредитов и подписок**, **начислением 10 кредитов каждому новому пользователю**, поддержкой **FSM**, webhook и деплоем на **Railway**.

---

## 🧩 Функционал бота

### Команды

#### `/start`

* Приветствие
* Пояснение работы бота
* У пользователя **10 стартовых кредитов**
* Инструкция по командам

---

#### `/photo`

FSM:

1. Пользователь присылает:

   * изображение
   * описание (prompt)

2. Выбор (по желанию):

   * модель — **текущая модель: `gpt-image-1`**
   * размер рамки: 512x512, 1024x1024

3. Стоимость генерации: **2 кредита**

4. После подтверждения:

   * списываются 2 кредита
   * запускается генерация через API

5. **Пример Конфигурации запроса к генератору изображений:**

```python
GEN_API_URL = "https://api.gen-api.ru/api/v1/networks/gpt-image-1" url = config.GEN_API_URL

files = [
    ("image[]", ("input.png", image_bytes, "image/png"))
]

payload = {
    "prompt": prompt,
    "model": "gpt-image-1",
    "quality": "low",
    "size": "1024x1024",
    "n": 1,
    "output_format": "png",
    "background": "auto",
    "moderation": "auto",
    "callback_url": config.CALLBACK_URL,
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

response = requests.post(
    config.GEN_API_URL,
    headers=headers,
    data=payload,
    files=files,
    timeout=30
)
```

6. После завершения генерации через webhook `/gen/callback` результат отправляется пользователю.

Пример вебхука

@app.post("/gen/callback") async def gen_callback(payload: dict): logger.info( "GEN CALLBACK\n" f"{json.dumps(payload, ensure_ascii=False, indent=2)}" ) request_id = payload.get("request_id") status = payload.get("status") if not request_id: raise HTTPException(400, "Missing request_id") task = get_task(request_id) if not task: logger.error(f"Unknown request_id={request_id}") return {"ok": False} chat_id = task["chat_id"] if status == "success": image_url = None if payload.get("result"): image_url = payload["result"][0] elif payload.get("full_response"): image_url = payload["full_response"][0].get("url")

---

#### `/buy_subscription`

* 3 плана: 200 ₽ — 10 кредитов, 500 ₽ — 25 кредитов, 1000 ₽ — 50 кредитов
* Платеж через ЮKassa
* Webhook `/yookassa/webhook`
* Начисление кредитов пользователю

Пример конфигурации запроса к ymoney

Configuration.account_id = YOOKASSA_SHOP_ID Configuration.secret_key = YOOKASSA_SECRET_KEY payment = Payment.create({ "amount": {"value": "500.00", "currency": "RUB"}, "confirmation": { "type": "redirect", "return_url": "https://t.me/convtalking263_bot?start=success" }, "description": f"Оплата доступа для {user_id}", "metadata": {"user_id": user_id}, "capture": True, }, uuid.uuid4()) payment_url = payment.confirmation.confirmation_url

Пример вебхука для обработки. url для вебхук изначально получить в ngrok

@app.post("/yookassa/webhook") async def yookassa_webhook(request: Request): data = await request.json() logging.info(f"Webhook received: {data}") if data.get("event") == "payment.succeeded": user_id = int(data["object"]["metadata"]["user_id"]) users_with_access.add(user_id) try: await bot.send_message(user_id, "✅ Оплата прошла! Доступ открыт.") except Exception as e: logging.error(f"Не удалось отправить сообщение: {e}")


---

#### `/status`

* Показать:

  * текущие кредиты
  * активную подписку

---

## 🏗 Структура проекта

```
.
├── .env
├── main.py
├── config/
│   └── settings.py
├── handlers/
│   ├── start.py
│   ├── photo.py
│   ├── subscription.py
│   └── status.py
├── states/
│   └── image_generation.py
├── services/
│   └── image_generation/
│       ├── client.py
│       └── tasks.py
├── payments/
│   ├── yookassa_client.py
│   └── webhook.py
├── database/
│   ├── base.py
│   ├── models.py
│   └── session.py
├── webhooks/
│   ├── gen_callback.py
│   └── yookassa.py
├── scripts/
│   └── run_local.sh
└── README.md
```

---

## 🧪 Технологии

* Python 3.12
* aiogram 3
* FastAPI
* SQLAlchemy async
* yookassa
* PostgreSQL
* ngrok (для локальной разработки)
* Railway (прод)

---

## 🚀 Деплой и запуск

* `.env` для всех ключей и URL
* Локальный запуск через bash-скрипт

