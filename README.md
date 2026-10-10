# Mehrli Telegram bot

18+ foydalanuvchilar uchun mehribon virtual suhbatdosh MVP-si. Unda personaj tanlash, kunlik bepul limit, Telegram Stars orqali qo'shimcha xabarlar va so'nggi suhbatlarni saqlash bor.

## Ishga tushirish

1. Python 3.10 yoki yangiroq versiyasini o'rnating.
2. `pip install -r requirements.txt` ni ishga tushiring.
3. `.env.example` nusxasini `.env` nomi bilan yarating va `TELEGRAM_BOT_TOKEN` hamda `OPENAI_API_KEY` qiymatlarini kiriting.
4. `python app.py` buyrug'i bilan botni ishga tushiring.

BotFather orqali bot yarating va tokenini `.env` ga qo'ying. Stars to'lovlarining ishlab chiqish shartlarini Telegram hujjatlariga muvofiq tekshirib, avval sinov muhitida sinang.

## Docker va cloud deploy

Loyiha Docker orqali Railway, Render, Fly.io yoki o'zingizning VPS'ingizda ishlaydi. Hosting servisining Environment Variables bo'limiga quyidagilarni kiriting:

- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (ixtiyoriy; standart: `gpt-5.5`)

`DATABASE_PATH` standart holatda konteyner ichidagi SQLite fayliga qaraydi. Cloud servis qayta ishga tushganda ma'lumotlar yo'qolmasligi uchun doimiy disk ulang yoki keyingi ishlab chiqish bosqichida PostgreSQL ga o'ting.

## Hozir bor funksiyalar

- 18+ tasdiqlovi va AI ekanini ochiq aytish
- `/qiz` va `/yigit` personaj uslublari
- Kuniga 10 ta bepul xabar
- `/sotibol` — 50 Stars evaziga 100 ta xabar
- SQLite orqali balans va qisqa kontekst xotirasi
- Qaramlikni kuchaytirish, erotik kontent va xavfli ruhiy holatlarga qarshi prompt chegaralari

## Keyingi bosqich

Rasm yuborishdan oldin alohida rasm krediti, moderatsiya, foydalanuvchi ma'lumotlarini o'chirish buyrug'i va maxfiylik siyosatini qo'shing. AI kalitlarini hech qachon Git-ga yubormang.
