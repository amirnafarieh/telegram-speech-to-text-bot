import os
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
import speech_recognition as sr
from pydub import AudioSegment
import re

# خواندن توکن از متغیر محیطی
TOKEN = os.getenv("TELEGRAM_TOKEN")
recognizer = sr.Recognizer()

# پاسخ به /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ سلام! خوش اومدی به ربات تبدیل صدا به متن 🎧\n\n📤 لطفاً یک فایل صوتی (Voice یا MP3) ارسال کن تا متنش رو برات بنویسم ✍️")

# هندل پیام‌های صوتی Voice
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processing_message = await update.message.reply_text("⏳ در حال تبدیل صدا به متن هستیم... لطفاً چند لحظه صبر کن 🧠")

    file = await context.bot.get_file(update.message.voice.file_id)
    await file.download_to_drive("voice.ogg")

    audio = AudioSegment.from_file("voice.ogg", format="ogg")
    audio.export("converted.wav", format="wav")

    with sr.AudioFile("converted.wav") as source:
        audio_data = recognizer.record(source)
        try:
            result = recognizer.recognize_google(audio_data, language="fa-IR", show_all=True)

            if not result or "alternative" not in result:
                await processing_message.delete()
                await update.message.reply_text("❌ متنی شناسایی نشد. لطفاً دوباره امتحان کن.")
                return

            full_text = result["alternative"][0]["transcript"]
            sentences = re.split(r'[.،؛!؟]\s*', full_text)
            sentences = [s.strip() for s in sentences if s.strip()]

            await processing_message.delete()
            for sentence in sentences:
                await update.message.reply_text(f"📝 {sentence}")

            with open("transcription.txt", "w", encoding="utf-8") as f:
                f.write(full_text)
            await update.message.reply_document(open("transcription.txt", "rb"))

            await update.message.reply_text("📩 فایل متنی برات فرستاده شد.\n\n🎧 برای تبدیل فایل بعدی، لطفاً یک صدا یا موسیقی دیگه بفرست 😊")

        except sr.UnknownValueError:
            await processing_message.delete()
            await update.message.reply_text("🤷‍♂️ متأسفم، نتونستم صدای شما رو بفهمم.")
        except sr.RequestError:
            await processing_message.delete()
            await update.message.reply_text("⚠️ خطا در ارتباط با سرور Google. لطفاً بعداً امتحان کن.")

# هندل فایل‌های صوتی Audio
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processing_message = await update.message.reply_text("⏳ در حال تبدیل صدا به متن هستیم... لطفاً چند لحظه صبر کن 🧠")

    file = await context.bot.get_file(update.message.audio.file_id)
    filename = update.message.audio.file_name or "audio.mp3"
    await file.download_to_drive(filename)

    audio = AudioSegment.from_file(filename)
    audio.export("converted.wav", format="wav")

    with sr.AudioFile("converted.wav") as source:
        audio_data = recognizer.record(source)
        try:
            result = recognizer.recognize_google(audio_data, language="fa-IR", show_all=True)

            if not result or "alternative" not in result:
                await processing_message.delete()
                await update.message.reply_text("❌ متنی شناسایی نشد. لطفاً دوباره امتحان کن.")
                return

            full_text = result["alternative"][0]["transcript"]
            sentences = re.split(r'[.،؛!؟]\s*', full_text)
            sentences = [s.strip() for s in sentences if s.strip()]

            await processing_message.delete()
            for sentence in sentences:
                await update.message.reply_text(f"📝 {sentence}")

            with open("transcription.txt", "w", encoding="utf-8") as f:
                f.write(full_text)
            await update.message.reply_document(open("transcription.txt", "rb"))

            await update.message.reply_text("📩 فایل متنی برات فرستاده شد.\n\n🎧 برای تبدیل فایل بعدی، لطفاً یک صدا یا موسیقی دیگه بفرست 😊")

        except sr.UnknownValueError:
            await processing_message.delete()
            await update.message.reply_text("🤷‍♂️ متأسفم، نتونستم صدای شما رو بفهمم.")
        except sr.RequestError:
            await processing_message.delete()
            await update.message.reply_text("⚠️ خطا در ارتباط با سرور Google. لطفاً بعداً امتحان کن.")

# اجرای ربات
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
