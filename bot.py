import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Config (loaded from environment variables on Railway)
# ------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
IMAGE_API = "https://image.pollinations.ai/prompt/{}"


# ------------------------------------------------------------------
# /start
# ------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Welcome to *MottunBot*!\n\n"
        "Here's what I can do:\n"
        "📖 /define <word> — Get the meaning of a word\n"
        "🎨 /imagine <description> — Generate an AI image\n"
        "❓ /help — Show this message again"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ------------------------------------------------------------------
# /help
# ------------------------------------------------------------------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ------------------------------------------------------------------
# /define <word> — Dictionary lookup
# ------------------------------------------------------------------
async def dictionary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /define <word>\nExample: /define serendipity")
        return

    word = " ".join(context.args)

    try:
        res = requests.get(DICTIONARY_API.format(word), timeout=10)
    except requests.RequestException:
        await update.message.reply_text("⚠️ Network error. Please try again.")
        return

    if res.status_code != 200:
        await update.message.reply_text(f"❌ No definition found for '{word}'.")
        return

    try:
        data = res.json()[0]
    except (ValueError, IndexError, KeyError):
        await update.message.reply_text(f"❌ Couldn't parse definition for '{word}'.")
        return

    phonetic = data.get("phonetic", "")
    meanings = data.get("meanings", [])

    reply = f"📖 *{word.capitalize()}* {phonetic}\n\n"
    for m in meanings[:3]:
        pos = m.get("partOfSpeech", "")
        reply += f"*{pos}*\n"
        for d in m.get("definitions", [])[:2]:
            reply += f"• {d.get('definition')}\n"
            if d.get("example"):
                reply += f"  _e.g. {d.get('example')}_\n"
        reply += "\n"

    await update.message.reply_text(reply, parse_mode="Markdown")


# ------------------------------------------------------------------
# /imagine <description> — AI image generation
# ------------------------------------------------------------------
async def imagine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /imagine <description>\nExample: /imagine a cat astronaut in space")
        return

    prompt = " ".join(context.args)
    status_msg = await update.message.reply_text("🎨 Generating your image, please wait...")

    encoded_prompt = requests.utils.quote(prompt)
    image_url = IMAGE_API.format(encoded_prompt)

    try:
        await update.message.reply_photo(photo=image_url, caption=f"🖼️ {prompt}")
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        await update.message.reply_text("⚠️ Sorry, I couldn't generate that image. Try a different prompt.")
    finally:
        await status_msg.delete()


# ------------------------------------------------------------------
# Fallback for unknown commands
# ------------------------------------------------------------------
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤔 I don't recognize that command. Try /help")


# ------------------------------------------------------------------
# Main entrypoint
# ------------------------------------------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("define", dictionary))
    app.add_handler(CommandHandler("imagine", imagine))
    app.add_handler(CommandHandler(["d"], dictionary))    # short alias
    app.add_handler(CommandHandler(["i"], imagine))       # short alias

    logger.info("MottunBot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
