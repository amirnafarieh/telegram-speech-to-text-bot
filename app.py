import os
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, ContextTypes, filters
import speech_recognition as sr
from pydub import AudioSegment

TOKEN = os.getenv("TELEGRAM_TOKEN")
recognizer = sr.Recognizer()
user_transcripts = {}  # حافظه موقت برای متن هر کاربر

# پاسخ به /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ سلام! خوش اومدی به ربات تبدیل صدا به متن 🎧\n\n📤 لطفاً یک فایل صوتی (Voice یا MP3) ارسال کن تا متنش رو برات بنویسم ✍️"
    )

# نوار پیشرفت ساختگی
async def show_fake_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Update:
    progress_phases = [
        "🎧 در حال تبدیل صدا به متن هستیم...\n▁▁▁▁▁▁▁▁",
        "🎧 در حال تبدیل صدا به متن هستیم...\n▁▂▂▂▂▂▂▂",
        "🎧 در حال تبدیل صدا به متن هستیم...\n▁▂▃▃▃▃▃▃",
        "🎧 در حال تبدیل صدا به متن هستیم...\n▁▂▃▄▄▄▄▄▄",
        "🎧 در حال تبدیل صدا به متن هستیم...\n▁▂▃▄▅▅▅▅",
        "🎧 در حال تبدیل صدا به متن هستیم...\n▁▂▃▄▅▆▆▆",
        "🎧 در حال تبدیل صدا به متن هستیم...\n▁▂▃▄▅▆▇▇",
        "🎧 در حال تبدیل صدا به متن هستیم...\n▁▂▃▄▅▆▇█",
    ]
    msg = await update.message.reply_text(progress_phases[0])
    for phase in progress_phases[1:]:
        await asyncio.sleep(0.4)
        await msg.edit_text(phase)
    return msg

# پردازش صوت
async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    progress_msg = await show_fake_progress(update, context)

    audio = AudioSegment.from_file(file_path)
    audio.export("converted.wav", format="wav")

    with sr.AudioFile("converted.wav") as source:
        audio_data = recognizer.record(source)
        try:
            result = recognizer.recognize_google(audio_data, language="fa-IR", show_all=True)
            if not result or "alternative" not in result:
                await progress_msg.delete()
                await update.message.reply_text("❌ متنی شناسایی نشد. لطفاً دوباره امتحان کن.")
                return

            full_text = result["alternative"][0]["transcript"]
            sentences = re.split(r'[.،؛!؟]\s*', full_text)
            sentences = [s.strip() for s in sentences if s.strip()]

            await progress_msg.delete()

            for sentence in sentences:
                await update.message.reply_text(f"📝 {sentence}")

            # ذخیره متن کاربر
            user_transcripts[update.effective_user.id] = sentences

            # ارسال دکمه‌ها
            keyboard = [
                [
                    InlineKeyboardButton("📄 دریافت فایل متنی (.txt)", callback_data="send_txt"),
                    InlineKeyboardButton("🎬 دریافت زیرنویس (.srt)", callback_data="send_srt"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("💾 کدوم فایل رو می‌خوای دریافت کنی؟", reply_markup=reply_markup)

        except sr.UnknownValueError:
            await progress_msg.delete()
            await up
