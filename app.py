import os
import re
import json
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import speech_recognition as sr
from pydub import AudioSegment

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 130657071
USAGE_FILE = "usage.json"
PREMIUM_FILE = "premium.json"
recognizer = sr.Recognizer()
user_transcripts = {}

# ---------- ابزارهای ذخیره ----------

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def today():
    return str(datetime.date.today())

def increase_usage(user_id):
    usage = load_json(USAGE_FILE)
    usage.setdefault("daily", {}).setdefault(today(), {}).setdefault(str(user_id), 0)
    usage["daily"][today()][str(user_id)] += 1
    save_json(USAGE_FILE, usage)

def get_usage_count(user_id):
    usage = load_json(USAGE_FILE)
    return usage.get("daily", {}).get(today(), {}).get(str(user_id), 0)

# ---------- مدیریت اشتراک ----------

def is_premium(user_id):
    premiums = load_json(PREMIUM_FILE)
    exp = premiums.get(str(user_id))
    if not exp:
        return False
    return datetime.date.fromisoformat(exp) >= datetime.date.today()

def add_premium(user_id, days):
    premiums = load_json(PREMIUM_FILE)
    now = datetime.date.today()
    new_exp = now + datetime.timedelta(days=days)
    premiums[str(user_id)] = new_exp.isoformat()
    save_json(PREMIUM_FILE, premiums)

# ---------- دستورات ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ سلام! فایل صوتی بفرست تا برات متنشو بنویسم. هر روز تا ۱۰ فایل رایگان ✨")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📢 برای دریافت اشتراک نامحدود:\n\n"
        "💳 شماره کارت: 1234-5678-9012-3456\n"
        "به یکی از مبالغ زیر پرداخت کنید:\n\n"
        "▪️ ۵۰ هزار تومان → ۳۱ روز\n"
        "▪️ ۱۰۰ هزار تومان → ۹۳ روز\n"
        "▪️ ۳۵۰ هزار تومان → ۳۶۶ روز\n\n"
        "سپس روی دکمه زیر بزن و رسید پرداخت رو ارسال کن:"
    )
    keyboard = [[InlineKeyboardButton("📤 ارسال رسید پرداخت", callback_data="send_receipt")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_receipt_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🧾 لطفاً رسید پرداخت را به صورت تصویر یا متن ارسال کنید.\nادمین بررسی خواهد کرد.")
    # اطلاع‌رسانی به ادمین
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 کاربر @{query.from_user.username or 'بدون نام'} ({query.from_user.id}) گفته رسید پرداخت داره.\n✅ برای تأیید از /confirm <user_id> <days> استفاده کن."
    )

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) == 2 and args[0].isdigit() and args[1].isdigit():
        user_id, days = int(args[0]), int(args[1])
        add_premium(user_id, int(days))
        await update.message.reply_text(f"✅ دسترسی نامحدود به کاربر {user_id} برای {days} روز فعال شد.")
        try:
            await context.bot.send_message(chat_id=user_id, text="🎉 اشتراک شما با موفقیت فعال شد! حالا محدودیت ندارید.")
        except:
            pass
    else:
        await update.message.reply_text("فرمت درست: /confirm <user_id> <days>")

# ---------- پردازش فایل ----------

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_premium(user_id):
        count = get_usage_count(user_id)
        if count >= 10:
            await update.message.reply_text("🚫 شما امروز به سقف ۱۰ فایل رایگان رسیدی.\nبرای نامحدود شدن از /subscribe استفاده کن.")
            return
        increase_usage(user_id)

    file = await context.bot.get_file(update.message.voice.file_id if update.message.voice else update.message.audio.file_id)
    filename = "input.ogg" if update.message.voice else (update.message.audio.file_name or "audio.mp3")
    await file.download_to_drive(filename)

    audio = AudioSegment.from_file(filename)
    audio.export("converted.wav", format="wav")

    with sr.AudioFile("converted.wav") as source:
        audio_data = recognizer.record(source)
        try:
            result = recognizer.recognize_google(audio_data, language="fa-IR", show_all=True)
            if not result or "alternative" not in result:
                await update.message.reply_text("❌ متنی شناسایی نشد.")
                return
            full_text = result["alternative"][0]["transcript"]
            sentences = re.split(r'[.،؛!؟]\s*', full_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            for sentence in sentences:
                await update.message.reply_text(f"📝 {sentence}")
        except:
            await update.message.reply_text("⚠️ خطایی در تبدیل صدا به متن رخ داد.")

# ---------- اجرای ربات ----------

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CallbackQueryHandler(handle_receipt_request, pattern="send_receipt"))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
