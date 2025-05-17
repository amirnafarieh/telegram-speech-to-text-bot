import os
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
import speech_recognition as sr
from pydub import AudioSegment
import re

# خواندن توکن از محیط Railway
TOKEN = os.getenv("TELEGRAM_TOKEN")
recognizer = sr.Recognizer()

# پیام /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لطفاً یک فایل صوتی (Voice یا MP3) بفرستید تا تبدیل به متن شود.")

# تابع مشترک برای پردازش و پاسخ‌دهی
async def process_audio(file_path: str, update: Update, processing_message):
    audio = AudioSegment.from_file(file_path)
    audio.export("converted.wav", format="wav")

    with sr.AudioFile("converted.wav") as source:
        audio_data = recognizer.record(source)
        try:
            result = recognizer.recognize_google(audio_data, language="fa-IR", show_all=True)

            if not result or "alternative" not in result:
                await processing_message.delete()
                await update.message.reply_text("متنی شناسایی نشد.")
                return

            full_text = result["alternative"][0]["transcript"]

            # تقسیم هوشمند متن به جمله‌ها
            if re.search(r'[.،؛!؟]', full_text):
                raw_sentences = re.split(r'(?<=[.،؛!؟])\s+', full_text)
            else:
                words = full_text.split()
                raw_sentences = [' '.join(words[i:i+15]) for i in range(0, len(words), 15)]

            sentences = [s.strip() for s in raw_sentences if s.strip()]

            await processing_message.delete()

            for sentence in sentences:
                await update.message.reply_text(sentence)

            # ارسال فایل متنی
            with open("transcription.txt", "w", encoding="utf-8") as f:
                f.write(full_text)

            await update.message.reply_document(open("transcription.txt", "rb"))
            await update.message.reply_text("برای تبدیل فایل بعدی، لطفاً فایل صوتی دیگری ارسال کنید.")

        except sr.UnknownValueError:
            await processing_message.delete()
            await update.message.reply_text("نتونستم متن رو تشخیص بدم 😔")
        except sr.RequestError:
            await processing_message.delete()
            await update.message.reply_text("خطا در ارتباط با سرور Google Speech!")

# هندل Voice
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processing_message = await update.message.reply_text("در حال تبدیل صدا به متن هستیم... لطفاً کمی منتظر باشید.")
    file = await context.bot.get_file(update.message.voice.file_id)
    await file.download_to_drive("voice.ogg")
    await process_audio("voice.ogg", update, processing_message)

# هندل Audio
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processing_message = await update.message.reply_text("در حال تبدیل صدا به متن هستیم... لطفاً کمی منتظر باشید.")
    file = await context.bot.get_file(update.message.audio.file_id)
    filename = update.message.audio.file_name or "audio.mp3"
    await file.download_to_drive(filen
