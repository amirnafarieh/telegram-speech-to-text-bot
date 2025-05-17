import os
import telegram
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import speech_recognition as sr
from pydub import AudioSegment
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی از فایل .env (این بخش فقط برای محیط‌های لوکال است)
# در Railway نیازی به این خط نیست زیرا متغیرهای محیطی در تنظیمات Railway تنظیم می‌شوند
load_dotenv()

# خواندن توکن از متغیر محیطی
TOKEN = os.getenv('TELEGRAM_TOKEN')  # توکن را از متغیر محیطی می‌خوانیم

# راه‌اندازی ربات
updater = Updater(TOKEN)

# تشخیص گفتار
recognizer = sr.Recognizer()

# تابع start برای پاسخ به دستور /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("سلام! لطفا فایل صوتی ارسال کنید.")

# تابع برای پردازش فایل صوتی و تبدیل به متن
def handle_audio(update: Update, context: CallbackContext) -> None:
    file = update.message.audio.get_file()
    file.download('audio.mp3')  # دانلود فایل به صورت MP3

    # تبدیل MP3 به WAV (speech_recognition فقط فایل WAV را می‌پذیرد)
    audio = AudioSegment.from_mp3('audio.mp3')
    audio.export('audio.wav', format='wav')

    # تبدیل فایل صوتی به متن
    with sr.AudioFile('audio.wav') as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language='fa-IR')  # تبدیل به متن فارسی
            update.message.reply_text(f"متن شناسایی‌شده: {text}")

            # ارسال فایل متنی
            with open("transcription.txt", "w", encoding="utf-8") as f:
                f.write(text)
            
            update.message.reply_document(document=open("transcription.txt", "rb"))

        except sr.UnknownValueError:
            update.message.reply_text("متاسفانه نتواستم چیزی بشنوم.")
        except sr.RequestError:
            update.message.reply_text("خطا در ارتباط با سرویس شناسایی صوت.")

# افزودن هندلرها
updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(MessageHandler(Filters.audio, handle_audio))

# شروع ربات
updater.start_polling()
updater.idle()
