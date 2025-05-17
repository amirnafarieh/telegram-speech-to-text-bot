import os
import whisper
from pydub import AudioSegment
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from flask import Flask, request
import logging

# ایجاد اپلیکیشن Flask
app = Flask(__name__)

# بارگذاری مدل Whisper
model = whisper.load_model("base")  # مدل Whisper را بارگذاری می‌کنیم

# تبدیل فایل MP3 به WAV
def convert_mp3_to_wav(mp3_file):
    audio = AudioSegment.from_mp3(mp3_file)
    wav_file = "audio.wav"
    audio.export(wav_file, format="wav")
    return wav_file

# تابع تبدیل گفتار به متن با استفاده از Whisper
def transcribe_audio(wav_file):
    result = model.transcribe(wav_file, language="fa")  # زبان فارسی
    return result['text']

# فرمان شروع برای ربات
def start(update: Update, context: CallbackContext):
    update.message.reply_text("سلام! لطفا یک فایل صوتی ارسال کنید.")

# دریافت فایل صوتی از کاربر و تبدیل آن به متن
def handle_audio(update: Update, context: CallbackContext):
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
    
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # اضافه کردن هندلرها
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.audio, handle_audio))

    # شروع ربات
    updater.start_polling()
    updater.idle()

# اجرای ربات در Flask
@app.route('/')
def hello():
    return "Bot is running!"

if __name__ == '__main__':
    from threading import Thread
    thread = Thread(target=main)
    thread.start()
    app.run(host='0.0.0.0', port=5000)
