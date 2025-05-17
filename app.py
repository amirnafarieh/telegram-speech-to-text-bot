import os
import speech_recognition as sr
from pydub import AudioSegment
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from flask import Flask
import logging

# تنظیمات برای شروع Flask
app = Flask(__name__)

# فرمان شروع برای ربات
def start(update: Update, context: CallbackContext):
    update.message.reply_text("سلام! خوش آمدید. لطفاً یک فایل صوتی ارسال کنید تا متن آن را دریافت کنید.")

# تبدیل MP3 به WAV
def convert_mp3_to_wav(mp3_file):
    audio = AudioSegment.from_mp3(mp3_file)
    wav_file = "audio.wav"
    audio.export(wav_file, format="wav")
    return wav_file

# تبدیل گفتار به متن با استفاده از speech_recognition
def transcribe_audio(wav_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_file) as source:
        audio = recognizer.record(source)
    
    try:
        # استفاده از Google Web Speech API برای تبدیل گفتار به متن
        transcription = recognizer.recognize_google(audio, language="fa-IR")
        return transcription
    except sr.UnknownValueError:
        return "نمی‌توانم متن را تشخیص دهم"
    except sr.RequestError as e:
        return f"خطا در درخواست: {e}"

# دریافت فایل صوتی از کاربر و تبدیل آن به متن
def handle_audio(update: Update, context: CallbackContext):
    # ارسال پیغام برای اطلاع‌رسانی به کاربر
    update.message.reply_text("در حال تبدیل فایل صوتی به متن هستیم، لطفاً منتظر بمانید...")

    # دانلود فایل صوتی
    file = update.message.audio.get_file()
    file.download("user_audio.mp3")

    # تبدیل فایل MP3 به WAV
    wav_file = convert_mp3_to_wav("user_audio.mp3")
    
    # تبدیل گفتار به متن
    transcription = transcribe_audio(wav_file)
    
    # ارسال متن به کاربر
    update.message.reply_text(f"متن استخراج شده: \n{transcription}")

# تنظیمات ربات تلگرام
def main():
    # توکن API ربات تلگرام خود را اینجا وارد کنید
    TOKEN = os.getenv("TELEGRAM_API_TOKEN")
    
    # تنظیمات Updater برای ارتباط با تلگرام
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # اضافه کردن هندلرها برای فرمان‌های ربات
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.audio, handle_audio))

    # شروع ربات تلگرام
    updater.start_polling()
    updater.idle()

# اجرای ربات در Flask
@app.route('/')
def hello():
    return "Bot is running!"

if __name__ == '__main__':
    # شروع ربات تلگرام در رشته اصلی (main thread)
    main()
    app.run(host='0.0.0.0', port=5000)
