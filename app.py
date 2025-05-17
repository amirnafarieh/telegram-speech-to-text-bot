import os
import re
import json
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import speech_recognition as sr
from pydub import AudioSegment

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_USERNAME = "@amirnafarieh_co"
ADMIN_ID = 130657071
recognizer = sr.Recognizer()
user_transcripts = {}

USAGE_FILE = "usage.json"
DAILY_LIMIT = 10

# --- ابزارهای مدیریت مصرف ---

def load_usage():
    if not os.path.exists(USAGE_FILE):
        return {"free": {}, "unlimited": []}
    with open(USAGE_FILE, "r") as f:
        return json.load(f)

def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)

def get_today_key():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")

def is_unlimited(user_id, usage_data):
    return user_id == ADMIN_ID or str(user_id) in usage_data.get("unlimited", [])

def can_use(user_id):
    usage = load_usage()
    if is_unlimited(user_id, usage):
        return True
    today = get_today_key()
    used = usage.get("free", {}).get(str(user_id), {}).get(today, 0)
    return used < DAILY_LIMIT

def increment_usage(user_id):
    usage = load_usage()
    if is_unlimited(user_id, usage):
        return
    today = get_today_key()
    usage.setdefault("free", {}).setdefault(str(user_id), {}).setdefault(today, 0)
    usage["free"][str(user_id)][today] += 1
    save_usage(usage)

# --- بررسی عضویت در کانال ---

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

# --- شروع ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ خوش اومدی! برای استفاده رایگان از ربات، عضو کانال زیر شو:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/amirnafarieh_co")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
        ])
    )

async def handle_join_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if await check_membership(user_id, context):
        await query.edit_message_text("✅ عضویت شما تأیید شد. حالا فایل صوتی بفرست 🎧")
    else:
        await query.edit_message_text("❌ هنوز عضو نشدی! عضو شو و دوباره تلاش کن.")

# --- فایل صوتی ---

async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    user_id = update.effective_user.id
    if not await check_membership(user_id, context):
        await update.message.reply_text("🔒 اول باید عضو کانال بشی:\nhttps://t.me/amirnafarieh_co")
        return
    if not can_use(user_id):
        await update.message.reply_text("🚫 شما به سقف استفاده روزانه رسیدید (۱۰ فایل صوتی).\n🕛 فردا دوباره امتحان کن.")
        return

    processing_msg = await update.message.reply_text("⏳ در حال تبدیل صدا به متن هستیم... لطفاً صبر کن 🧠")
    audio = AudioSegment.from_file(file_path)
    audio.export("converted.wav", format="wav")

    with sr.AudioFile("converted.wav") as source:
        audio_data = recognizer.record(source)
        try:
            result = recognizer.recognize_google(audio_data, language="fa-IR", show_all=True)
            if not result or "alternative" not in result:
                await processing_msg.delete()
                await update.message.reply_text("❌ متنی شناسایی نشد. لطفاً دوباره امتحان کن.")
                return

            full_text = result["alternative"][0]["transcript"]
            sentences = re.split(r'[.،؛!؟]\s*', full_text)
            sentences = [s.strip() for s in sentences if s.strip()]

            await processing_msg.delete()
            for sentence in sentences:
                await update.message.reply_text(f"📝 {sentence}")

            user_transcripts[user_id] = sentences
            increment_usage(user_id)

            await update.message.reply_text(
                "💾 مایلید کدوم فایل رو دریافت کنید؟",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📄 فایل متنی (.txt)", callback_data="send_txt"),
                     InlineKeyboardButton("🎬 زیرنویس (.srt)", callback_data="send_srt")]
                ])
            )
        except sr.UnknownValueError:
            await processing_msg.delete()
            await update.message.reply_text("🤷‍♂️ متأسفم، نتونستم صدای شما رو بفهمم.")
        except sr.RequestError:
            await processing_msg.delete()
            await update.message.reply_text("⚠️ خطا در ارتباط با Google. لطفاً بعداً امتحان کن.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.voice.file_id)
    await file.download_to_drive("voice.ogg")
    await process_audio(update, context, "voice.ogg")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.audio.file_id)
    filename = update.message.audio.file_name or "audio.mp3"
    await file.download_to_drive(filename)
    await process_audio(update, context, filename)

# --- ارسال فایل‌ها ---

async def handle_file_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    sentences = user_transcripts.get(user_id)

    if not sentences:
        await query.edit_message_text("❗ هیچ متنی پیدا نشد. لطفاً یک فایل صوتی ارسال کن.")
        return

    if query.data == "send_txt":
        with open("transcription.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(sentences))
        await context.bot.send_document(chat_id=query.message.chat.id, document=open("transcription.txt", "rb"))

    elif query.data == "send_srt":
        with open("transcription.srt", "w", encoding="utf-8") as f:
            for i, sentence in enumerate(sentences, start=1):
                start = f"00:00:{i:02},000"
                end = f"00:00:{i+1:02},000"
                f.write(f"{i}\n{start} --> {end}\n{sentence}\n\n")
        await context.bot.send_document(chat_id=query.message.chat.id, document=open("transcription.srt", "rb"))

    await query.edit_message_text("✅ فایل موردنظر برای شما ارسال شد.")

# --- پنل ادمین ---

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    await update.message.reply_text("🛠️ پنل ادمین فعال است.\nبرای افزودن دسترسی نامحدود:\n`/add_unlimited <user_id>`")

async def add_unlimited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❗ لطفاً آیدی عددی کاربر را وارد کنید.")
        return
    target_id = context.args[0]
    usage = load_usage()
    if target_id not in usage.get("unlimited", []):
        usage.setdefault("unlimited", []).append(target_id)
        save_usage(usage)
        await update.message.reply_text(f"✅ کاربر {target_id} به لیست نامحدود اضافه شد.")
    else:
        await update.message.reply_text("ℹ️ این کاربر قبلاً در لیست نامحدود بوده است.")

# --- اجرای ربات ---

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("add_unlimited", add_unlimited))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(CallbackQueryHandler(handle_file_buttons, pattern="send_"))
    app.add_handler(CallbackQueryHandler(handle_join_check, pattern="check_membership"))
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
