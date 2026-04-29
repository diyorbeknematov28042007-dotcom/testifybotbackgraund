# Testify Bot

## O'rnatish

### 1. Bot yaratish
1. @BotFather ga yozing → /newbot
2. Token nusxalab oling

### 2. .env fayl yarating
```
BOT_TOKEN=sizning_token
ADMIN_ID=sizning_telegram_id
WEBHOOK_HOST=https://sizning-bot.onrender.com
PORT=8080
```

### 3. Render.com ga deploy

1. GitHub'ga yuklang
2. Render.com → New Web Service
3. Sozlamalar:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. Environment Variables qo'shing:
   - BOT_TOKEN
   - ADMIN_ID
   - WEBHOOK_HOST = https://sizning-bot.onrender.com
   - PORT = 8080
5. Deploy!

## Foydalanish

- /start — Botni boshlash
- /admin — Admin panel (faqat adminlar)
- /cancel — Amalni bekor qilish

## Admin imkoniyatlari

- 📢 Ommaviy post — barcha foydalanuvchilarga xabar
- 📊 Statistika — foydalanuvchilar soni
- 📋 Kanallar — majburiy obuna kanallarini boshqarish
- 👥 Adminlar — admin qo'shish/o'chirish
- ✏️ Salomlashuv — /start xabarini tahrirlash
