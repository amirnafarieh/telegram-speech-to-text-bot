import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
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
CHANNEL_USERNAME = "@amirnafarieh_co"  # کانال تلگرامی برای بررسی عضویت
recognizer = sr.Recognizer()
user_transcripts = {}
pending_users = set()  # برای نگهداری کاربران در صف بررسی عضویت

# پیغام شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ سلام! به ربات تبدیل صدا به متن خوش اومدی 🎧\n\n📥 برای استفاده رایگان از ربات، ابتدا عضو کانال زیر شو:\n👇👇👇\nhttps://t.me/amirnafarieh_co",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/amirnafarieh_co")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
        ])
    )
    pending_users.add(update.effective_user.id)

# بررسی عضویت در کانال
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member: ChatMember = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        return False

# وقتی کاربر روی "عضو شدم" کلیک می‌کنه
async def handle_join_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if await check_membership(user_id, context):
        await query.edit_message_text("✅ عضویت شما تأیید شد. حالا می‌تونید فایل صوتی ارسال کنید 🎧")
        pending_users.discard(user_id)
    else:
        await query.edit_message_text("❌ هنوز عضو کانال نشدی!\n\n📢 لطفاً ابتدا عضو کانال زیر شو:\nhttps://t.me/amirnafarieh_co")

# قبل از هر صوت، بررسی عضویت
async def pre_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in pending_users:
        await update.message.reply_text("🔒 برای استفاده از ربات ابتدا عضو کانال شو:\nhttps://t.me/amirnafarieh_co")
        return False

    if not await check_membership(user_id, context):
        pending_users.add(user_id)
        await update.message.reply_text(
            "🔐 برای استفاده از ربات، ابتدا باید عضو کانال بشی:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/amirnafarieh_co")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
            ])
        )
        return False

    return True

# تابع مشترک پردازش فایل صوتی
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
                await update.message.reply_text(f"📝 {sentence}")

            user_transcripts[update.effective_user.id] = sentences
            await update.message.reply_text(
                "💾 مایلید کدوم فایل رو دریافت کنید؟",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📄 دریافت فایل متنی (.txt)", callback_data="send_txt"),
                     InlineKeyboardButton("🎬 دریافت زیرنویس (.srt)", callback_data="send_srt")]
                ])
            )

        except sr.UnknownValueError:
            await processing_msg.delete()
            await update.message.reply_text("🤷‍♂️ متأسفم، نتونستم صدای شما رو بفهمم.")
        except sr.RequestError:
            await processing_msg.delete()
            await update.message.reply_text("⚠️ خطا در ارتباط با سرور Google. لطفاً بعداً امتحان کن.")

# هندل فایل voice
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await pre_check(update, context):
        return
    file = await context.bot.get_file(update.message.voice.file_id)
    await file.download_to_drive("voice.ogg")
    await process_audio(update, context, "voice.ogg")

# هندل فایل audio
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await pre_check(update, context):
        return
    file = await context.bot.get_file(update.message.audio.file_id)
    filename = update.message.audio.file_name or "audio.mp3"
    await file.download_to_drive(filename)
    await process_audio(update, context, filename)

# هندل دکمه دریافت فایل txt یا srt
async def handle_file_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    sentences = user_transcripts.get(user_id)

    if not sentences:
        await query.edit_message_text("❗ متنی برای ارسال یافت نشد. لطفاً ابتدا یک فایل صوتی بفرست.")
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
    app.add_handler(CallbackQueryHandler(handle_file_buttons, pattern="send_"))
    app.add_handler(CallbackQueryHandler(handle_join_check, pattern="check_membership"))
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
