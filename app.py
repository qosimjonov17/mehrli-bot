"""Mehrli suhbatdosh Telegram botining boshlang'ich MVP-si."""

import logging
import os
import sqlite3
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.5")
DB_PATH = Path(os.environ.get("DATABASE_PATH", "data/companion.sqlite3"))
FREE_DAILY_MESSAGES = 10
STAR_PACK_PRICE = 50
STAR_PACK_MESSAGES = 100

SYSTEM_PROMPT = """
Sen Mehrli — foydalanuvchining virtual, mehribon suhbatdoshi san.
Har doim o'zbek tilida, tabiiy, qisqa va samimiy javob ber. Foydalanuvchining
tanlagan personaji va suhbat uslubiga moslash. Sen AI ekaningni yashirma va
haqiqiy inson yoki romantik sherik deb da'vo qilma.

Chegaralar: foydalanuvchini oila, do'stlar yoki mutaxassislardan uzoqlashtirma;
"faqat menga keraksan" kabi qaramlikni kuchaytiruvchi iboralarni ishlatma.
Erotik, jinsiy yoki ekspluatatsion suhbatga kirmagin. Voyaga yetmaganlar haqida
romantik yoki jinsiy rol o'ynamagin. O'ziga zarar yetkazish xavfi bo'lsa,
muloyimlik bilan yaqin inson va mahalliy shoshilinch yordamga murojaat qilishni
taklif et. Hukm qilma, lekin xavfsizlikni birinchi o'ringa qo'y.
""".strip()


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                age_confirmed INTEGER NOT NULL DEFAULT 0,
                persona TEXT NOT NULL DEFAULT 'mehribon do\'st',
                paid_messages INTEGER NOT NULL DEFAULT 0,
                daily_date TEXT NOT NULL DEFAULT '',
                daily_used INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)


def ensure_user(telegram_id: int, name: str) -> sqlite3.Row:
    with db() as con:
        con.execute(
            "INSERT OR IGNORE INTO users (telegram_id, name) VALUES (?, ?)",
            (telegram_id, name),
        )
        con.execute("UPDATE users SET name = ? WHERE telegram_id = ?", (name, telegram_id))
        return con.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()


def get_user(telegram_id: int) -> sqlite3.Row:
    with db() as con:
        return con.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()


def can_send(telegram_id: int) -> bool:
    today = date.today().isoformat()
    with db() as con:
        user = con.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if user["paid_messages"] > 0:
            return True
        return user["daily_date"] != today or user["daily_used"] < FREE_DAILY_MESSAGES


def use_message(telegram_id: int) -> None:
    today = date.today().isoformat()
    with db() as con:
        user = con.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if user["paid_messages"] > 0:
            con.execute("UPDATE users SET paid_messages = paid_messages - 1 WHERE telegram_id = ?", (telegram_id,))
        elif user["daily_date"] != today:
            con.execute("UPDATE users SET daily_date = ?, daily_used = 1 WHERE telegram_id = ?", (today, telegram_id))
        else:
            con.execute("UPDATE users SET daily_used = daily_used + 1 WHERE telegram_id = ?", (telegram_id,))


def save_message(telegram_id: int, role: str, content: str) -> None:
    with db() as con:
        con.execute("INSERT INTO messages (telegram_id, role, content) VALUES (?, ?, ?)", (telegram_id, role, content))


def history(telegram_id: int) -> list[dict[str, str]]:
    with db() as con:
        rows = con.execute(
            "SELECT role, content FROM messages WHERE telegram_id = ? ORDER BY id DESC LIMIT 12", (telegram_id,)
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user.id, user.first_name or "Do'st")
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("18 yoshdan kattaman", callback_data="age_yes")]])
    await update.message.reply_text(
        "Salom! Men Mehrli, ochiq va mehribon virtual suhbatdoshman. Men AI ekanimni yashirmayman. "
        "Bu bot faqat 18 yoshdan kattalar uchun. Davom etish uchun tasdiqlang.",
        reply_markup=keyboard,
    )


async def age_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    with db() as con:
        con.execute("UPDATE users SET age_confirmed = 1 WHERE telegram_id = ?", (query.from_user.id,))
    await query.edit_message_text(
        "Rahmat. Personajni tanlang: /qiz yoki /yigit\n\n"
        "Kuniga 10 ta xabar bepul. /balans orqali qoldiqni, /sotibol orqali xabar paketini ko'rasiz."
    )


async def set_persona(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update.effective_user.id, update.effective_user.first_name or "Do'st")
    persona = "mehribon qiz do'st" if update.message.text == "/qiz" else "mehribon yigit do'st"
    with db() as con:
        con.execute("UPDATE users SET persona = ? WHERE telegram_id = ?", (persona, update.effective_user.id))
    await update.message.reply_text(f"Zo'r, men endi {persona} uslubida suhbatlashaman. Nima haqida o'ylayapsiz?")


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user(update.effective_user.id) or ensure_user(
        update.effective_user.id, update.effective_user.first_name or "Do'st"
    )
    free_left = FREE_DAILY_MESSAGES if user["daily_date"] != date.today().isoformat() else max(0, FREE_DAILY_MESSAGES - user["daily_used"])
    await update.message.reply_text(f"Bugungi bepul xabarlar: {free_left}\nSotib olingan xabarlar: {user['paid_messages']}")


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="100 ta suhbat xabari",
        description="Mehrli botida qo'shimcha 100 ta xabar.",
        payload="messages_100",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice("100 ta xabar", STAR_PACK_PRICE)],
    )


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=update.pre_checkout_query.invoice_payload == "messages_100")


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment = update.message.successful_payment
    if payment.invoice_payload != "messages_100":
        return
    with db() as con:
        con.execute("UPDATE users SET paid_messages = paid_messages + ? WHERE telegram_id = ?", (STAR_PACK_MESSAGES, update.effective_user.id))
    await update.message.reply_text("To'lov qabul qilindi — hisobingizga 100 ta xabar qo'shildi. Davom etamiz 💛")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user = get_user(telegram_id) or ensure_user(telegram_id, update.effective_user.first_name or "Do'st")
    if not user["age_confirmed"]:
        await update.message.reply_text("Avval /start buyrug'i orqali 18+ tasdiqlovidan o'ting.")
        return
    if not can_send(telegram_id):
        await update.message.reply_text("Bugungi bepul xabarlar tugadi. /sotibol orqali davom ettirish uchun 100 ta xabar oling.")
        return
    text = update.message.text.strip()
    if not text:
        return
    use_message(telegram_id)
    save_message(telegram_id, "user", text)
    await update.effective_chat.send_action("typing")
    try:
        client = AsyncOpenAI()
        response = await client.responses.create(
            model=MODEL,
            instructions=f"{SYSTEM_PROMPT}\n\nTanlangan personaj: {user['persona']}",
            input=history(telegram_id),
            max_output_tokens=250,
        )
        answer = response.output_text.strip() or "Kechirasiz, hozir javob bera olmadim. Yana yozib ko'ring."
    except Exception:
        logger.exception("OpenAI request failed")
        answer = "Hozir ulanishda kichik muammo bor. Bir ozdan keyin yana yozing."
    save_message(telegram_id, "assistant", answer)
    await update.message.reply_text(answer)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Buyruqlar: /qiz, /yigit, /balans, /sotibol. Suhbat tarixi shu bot ichida saqlanadi.")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN .env faylida ko'rsatilmagan.")
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qiz", set_persona))
    app.add_handler(CommandHandler("yigit", set_persona))
    app.add_handler(CommandHandler("balans", balance))
    app.add_handler(CommandHandler("sotibol", buy))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(age_confirmation, pattern="^age_yes$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
