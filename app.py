import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, ContextTypes, filters
import speech_recognition as sr
from pydub import AudioSegment

TOKEN = os.getenv("TELEGRAM_TOKEN")
recognizer = sr.Recognizer()

# حافظه موقت برای ذخیره متن هر کاربر (user_id → text)
user_transcripts = {}

# پاسخ به /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ سلام! خوش اومدی به ربات تبدیل صدا به متن 🎧\n\n📤 لطفاً یک فایل صوتی (Voice یا MP3) ارسال کن تا متنش رو برات بنویسم ✍️"
    )

# تابع مشترک پردازش صدا
async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    processing_msg = await update.message.reply_text("⏳ در حال تبدیل صدا به متن هستیم... لطفاً چند لحظه صبر کن 🧠")

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
                await update.message.reply_text(f" {sentence}")

            # ذخیره متن در حافظه موقت برای ارسال بعدی
            user_transcripts[update.effective_user.id] = sentences

            # نمایش دکمه‌ها برای انتخاب فرمت فایل
            keyboard = [
                [
                    InlineKeyboardButton("📄 دریافت فایل متنی (.txt)", callback_data="send_txt"),
                    InlineKeyboardButton("🎬 دریافت زیرنویس (.srt)", callback_data="send_srt"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("💾 مایلید کدوم فایل رو دریافت کنید؟", reply_markup=reply_markup)

        except sr.UnknownValueError:
            await processing_msg.delete()
            await update.message.reply_text("🤷‍♂️ نتونستم صدای شما رو بفهمم.")
        except sr.RequestError:
            await processing_msg.delete()
            await update.message.reply_text("⚠️ خطا در ارتباط با سرور Google. لطفاً بعداً امتحان کن.")

# هندل پیام Voice
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.voice.file_id)
    await file.download_to_drive("voice.ogg")
    await process_audio(update, context, "voice.ogg")

# هندل پیام Audio
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.audio.file_id)
    filename = update.message.audio.file_name or "audio.mp3"
    await file.download_to_drive(filename)
    await process_audio(update, context, filename)

# هندل کلیک روی دکمه‌های فایل
async def handle_file_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    sentences = user_transcripts.get(user_id)

    if not sentences:
        await query.edit_message_text("❗ متنی برای ارسال یافت نشد. لطفاً یک فایل صوتی ارسال کنید.")
        return

    if query.data == "send_txt":
        with open("transcription.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(sentences))
        await context.bot.send_document(chat_id=query.message.chat.id, document=open("transcription.txt", "rb"))

    elif query.data == "send_srt":
        with open("transcription.srt", "w", encoding="utf-8") as f:
            for i, sentence in enumerate(sentences, start=1):
                start_time = f"00:00:{i:02},000"
                end_time = f"00:00:{i+1:02},000"
                f.write(f"{i}\n{start_time} --> {end_time}\n{sentence}\n\n")
        await context.bot.send_document(chat_id=query.message.chat.id, document=open("transcription.srt", "rb"))

    await query.edit_message_text("✅ فایل انتخابی برای شما ارسال شد.\n\n🎧 برای فایل بعدی، صدا بفرست 😊")

# اجرای ربات
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(CallbackQueryHandler(handle_file_request))
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
