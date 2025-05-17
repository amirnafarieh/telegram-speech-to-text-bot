import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import speech_recognition as sr
from pydub import AudioSegment

# خواندن توکن از متغیر محیطی
TOKEN = os.getenv('TELEGRAM_TOKEN')  # توکن را از متغیر محیطی می‌خوانیم

# راه‌اندازی ربات با استفاده از Application
application = Application.builder().token(TOKEN).build()

# تشخیص گفتار
recognizer = sr.Recognizer()

# تابع start برای پاسخ به دستور /start
async def start(update: Update, context: CallbackContext) -> None:
    """این تابع برای پاسخ به دستور /start است."""
    await update.message.reply_text("سلام! لطفا فایل صوتی ارسال کنید.")

# تابع برای پردازش فایل صوتی و تبدیل به متن
async def handle_audio(update: Update, context: CallbackContext) -> None:
    """این تابع فایل صوتی را دریافت کرده و آن را به متن تبدیل می‌کند."""
    
    # دریافت فایل صوتی
    file = await update.message.audio.get_file()
    
    # دانلود فایل به صورت MP3
    await file.download('audio.mp3')  # استفاده از متد download به جای download_as

    # تبدیل MP3 به WAV (speech_recognition فقط فایل WAV را می‌پذیرد)
    audio = AudioSegment.from_mp3('audio.mp3')
    audio.export('audio.wav', format='wav')

    # تبدیل فایل صوتی به متن
    with sr.AudioFile('audio.wav') as source:
        audio_data = recognizer.record(source)
        try:
            # شناسایی گفتار به زبان فارسی
            text = recognizer.recognize_google(audio_data, language='fa-IR')  
            await update.message.reply_text(f"متن شناسایی‌شده: {text}")

            # ارسال فایل متنی
            with open("transcription.txt", "w", encoding="utf-8") as f:
                f.write(text)
            
            await update.message.reply_document(document=open("transcription.txt", "rb"))

        except sr.UnknownValueError:
            await update.message.reply_text("متاسفانه نتواستم چیزی بشنوم.")
        except sr.RequestError:
            await update.message.reply_text("خطا در ارتباط با سرویس شناسایی صوت.")

# افزودن هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.AUDIO, handle_audio))

# شروع ربات
application.run_polling()
