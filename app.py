import os
import re
import json
import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
recognizer = sr.Recognizer()
user_transcripts = {}

USAGE_FILE = "usage.json"
SETTINGS_FILE = "settings.json"

LANGUAGES = {
    "fa": "فارسی 🇮🇷",
    "en": "انگلیسی 🇺🇸",
    "ar": "عربی 🇸🇦",
    "tr": "ترکی 🇹🇷"
}

# ----------------- Utility -----------------

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

def get_user_lang(user_id):
    settings = load_json(SETTINGS_FILE)
    return settings.get(str(user_id), "fa")

def set_user_lang(user_id, lang_code):
    settings = load_json(SETTINGS_FILE)
    settings[str(user_id)] = lang_code
    save_json(SETTINGS_FILE, settings)

def is_unlimited(user_id):
    usage = load_json(USAGE_FILE)
    return str(user_id) in usage.get("unlimited_users", [])

def increase_usage(user_id):
    usage = load_json(USAGE_FILE)
    usage.setdefault("daily", {}).setdefault(today(), {}).setdefault(str(user_id), 0)
    usage["daily"][today()][str(user_id)] += 1
    save_json(USAGE_FILE, usage)

def get_usage_count(user_id):
    usage = load_json(USAGE_FILE)
    return usage.get("daily", {}).get(today(), {}).get(str(user_id), 0)

def add_unlimited(user_id):
    usage = load_json(USAGE_FILE)
    usage.setdefault("unlimited_users", [])
    if str(user_id) not in usage["unlimited_users"]:
        usage["unlimited_users"].append(str(user_id))
    save_json(USAGE_FILE, usage)

# ----------------- Bot Logic -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ سلام! فایل صوتی بفرست تا برات تبدیل به متن کنم.\nهر روز می‌تونی تا 10 فایل رایگان استفاده کنی ✨"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if args and args[0].isdigit():
        add_unlimited(args[0])
        await update.message.reply_text(f"✅ دسترسی نامحدود به کاربر {args[0]} داده شد.")
    else:
        await update.message.reply_text("📌 برای افزودن کاربر نامحدود:\n`/admin 123456789`")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_unlimited(user_id):
        count = get_usage_count(user_id)
        if count >= 10:
            await update.message.reply_text("🚫 سقف استفاده روزانه شما (۱۰ فایل) پر شده است.\nفردا دوباره امتحان کن یا اشتراک نامحدود بگیر.")
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
            lang = get_user_lang(user_id)
            result = recognizer.recognize_google(audio_data, language=lang, show_all=True)
            if not result or "alternative" not in result:
                await update.message.reply_text("❌ متن شناسایی نشد.")
                return
            full_text = result["alternative"][0]["transcript"]
            sentences = re.split(r'[.،؛!؟]\s*', full_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            user_transcripts[user_id] = sentences

            for sentence in sentences:
                await update.message.reply_text(f"📝 {sentence}")

            # Action buttons
            keyboard = [
                [InlineKeyboardButton("✍️ ساخت کپشن اینستاگرامی", callback_data="caption")],
                [InlineKeyboardButton("📊 آمار مصرف من", callback_data="stats")],
                [InlineKeyboardButton("🌍 انتخاب زبان", callback_data="lang_select")]
            ]
            await update.message.reply_text("💡 انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

        except Exception:
            await update.message.reply_text("⚠️ خطایی رخ داد. لطفاً بعداً دوباره امتحان کن.")

# ----------------- Inline Button Callbacks -----------------

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "caption":
        if user_id not in user_transcripts:
            await query.edit_message_text("❗ ابتدا فایل صوتی ارسال کن.")
            return
        caption = "🌟 " + " ".join(user_transcripts[user_id])[:150] + "\n\n#متن #صدا #هوش_مصنوعی #تبدیل_صدا #ربات"
        await query.edit_message_text(f"📸 کپشن پیشنهادی:\n\n{caption}")

    elif query.data == "stats":
        count = get_usage_count(user_id)
        msg = f"📊 مصرف امروز شما: {count}/10 فایل"
        await query.edit_message_text(msg)

    elif query.data == "lang_select":
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"lang_{code}")]
            for code, name in LANGUAGES.items()
        ]
        await query.edit_message_text("🌍 لطفاً زبان موردنظر رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("lang_"):
        lang_code = query.data.split("_")[1]
        set_user_lang(user_id, lang_code)
        await query.edit_message_text(f"✅ زبان شما تنظیم شد به: {LANGUAGES[lang_code]}")

# ----------------- Main -----------------

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
