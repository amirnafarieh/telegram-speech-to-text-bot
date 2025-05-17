import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackContext,
    ContextTypes, filters
)

# ---------------- CONFIG ----------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 130657071
LIMIT_PER_DAY = 10
USAGE_FILE = "usage.json"
# ----------------------------------------

# حافظه مصرف کاربران
if not os.path.exists(USAGE_FILE):
    with open(USAGE_FILE, "w") as f:
        json.dump({"unlimited": [], "usage": {}}, f)

def load_usage():
    with open(USAGE_FILE, "r") as f:
        return json.load(f)

def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)

def today_key():
    return datetime.utcnow().strftime("%Y-%m-%d")

async def is_allowed(user_id: int) -> bool:
    data = load_usage()
    if str(user_id) in data["unlimited"]:
        return True
    usage = data["usage"].get(str(user_id), {}).get(today_key(), 0)
    return usage < LIMIT_PER_DAY

def increment_usage(user_id: int):
    data = load_usage()
    user_id = str(user_id)
    key = today_key()
    if user_id not in data["usage"]:
        data["usage"][user_id] = {}
    if key not in data["usage"][user_id]:
        data["usage"][user_id][key] = 0
    data["usage"][user_id][key] += 1
    save_usage(data)

def add_unlimited(user_id: int):
    data = load_usage()
    if str(user_id) not in data["unlimited"]:
        data["unlimited"].append(str(user_id))
        save_usage(data)

# ----------- HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ خوش آمدید!\n"
        "برای استفاده رایگان، می‌تونید روزانه حداکثر ۱۰ فایل صوتی (voice یا audio) ارسال کنید.\n"
        "ارسال فایل رو شروع کنید 🎧"
    )

async def handle_voice_or_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_allowed(user_id):
        await update.message.reply_text(
            "🚫 شما به سقف 10 فایل رایگان امروز رسیدید.\n"
            "🕒 لطفاً فردا دوباره امتحان کنید یا ادمین بهتون دسترسی نامحدود بده."
        )
        return

    increment_usage(user_id)
    await update.message.reply_text(
        "✅ فایل دریافت شد.\n"
        "⏳ در حال پردازش... (در این نسخه فقط شمارش فعال است)"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ فقط ادمین به این بخش دسترسی دارد.")
        return
    await update.message.reply_text(
        "🛠️ پنل ادمین:\n"
        "/add_unlimited <user_id> ➜ دسترسی نامحدود به کاربر"
    )

async def add_unlimited_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ فقط ادمین می‌تونه این کارو انجام بده.")
        return
    try:
        target_id = int(context.args[0])
        add_unlimited(target_id)
        await update.message.reply_text(f"✅ کاربر {target_id} اکنون دسترسی نامحدود دارد.")
    except Exception:
        await update.message.reply_text(
            "❌ فرمت اشتباه است.\nمثال:\n`/add_unlimited 123456789`",
            parse_mode="Markdown"
        )

# ----------- MAIN ----------------

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("add_unlimited", add_unlimited_cmd))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_or_audio))
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
