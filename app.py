from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from pydub import AudioSegment
import speech_recognition as sr

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # دریافت فایل Voice و دانلود آن به عنوان voice_note.ogg
    file_id = update.message.voice.file_id
    file = await context.bot.get_file(file_id)
    await file.download_to_drive(custom_path="voice_note.ogg")  # ذخیره پیام صوتی با نام voice_note.ogg

    # تبدیل فایل .ogg به .wav با استفاده از pydub/ffmpeg (برای استفاده در تشخیص گفتار)
    voice_audio = AudioSegment.from_file("voice_note.ogg", format="ogg")
    voice_audio.export("voice_note.wav", format="wav")

    # تبدیل گفتار به متن با SpeechRecognition (مثال با استفاده از سرویس Google)
    recognizer = sr.Recognizer()
    with sr.AudioFile("voice_note.wav") as source:
        audio_data = recognizer.record(source)
    text = recognizer.recognize_google(audio_data, language="fa-IR")
    await update.message.reply_text(f"متن تشخیص‌داده‌شده: {text}")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # دریافت فایل Audio و دانلود آن به عنوان audio_file.mp3 (یا پسوند اصلی فایل ارسالی)
    file_id = update.message.audio.file_id
    file = await context.bot.get_file(file_id)
    # استفاده از نام اصلی فایل در تلگرام در صورت موجود بودن
    default_filename = update.message.audio.file_name or "audio_file"
    await file.download_to_drive(custom_path=default_filename)  # مثلاً audio_file.mp3
    await update.message.reply_text("فایل صوتی شما ذخیره شد.")

if __name__ == "__main__":
    app = Application.builder().token("توکن-ربات-شما").build()
    # افزودن هندلرها برای پیام‌های صوتی و فایل‌های صوتی
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.run_polling()
