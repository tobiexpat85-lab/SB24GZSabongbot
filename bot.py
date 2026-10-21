import os
import json
import random
import logging
from datetime import date, time, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["BOT_TOKEN"]  # the only key needed
DAILY_HOUR_UTC = int(os.environ.get("DAILY_HOUR_UTC", "8"))  # when the daily riddle is sent
SUBS_FILE = "subscribers.json"

with open("riddles.json", encoding="utf-8") as f:
    RIDDLES = json.load(f)


# ---------- helpers ----------
def todays_index() -> int:
    """Same riddle for everyone on a given day, cycling through the list."""
    return date.today().toordinal() % len(RIDDLES)


def riddle_text(i: int, label: str) -> str:
    return f"🧩 *{label}*\n\n{RIDDLES[i]['q']}"


def reveal_keyboard(i: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("👀 Reveal answer", callback_data=f"ans:{i}")]]
    )


def load_subs() -> set:
    try:
        with open(SUBS_FILE) as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_subs(subs: set) -> None:
    with open(SUBS_FILE, "w") as f:
        json.dump(sorted(subs), f)


# ---------- commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm Riddle Bot 🧩\n\n"
        "/riddle – today's riddle\n"
        "/random – a random riddle\n"
        "/subscribe – get a riddle every day\n"
        "/unsubscribe – stop daily riddles"
    )


async def riddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    i = todays_index()
    await update.message.reply_text(
        riddle_text(i, "Riddle of the Day"),
        parse_mode="Markdown",
        reply_markup=reveal_keyboard(i),
    )


async def random_riddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    i = random.randrange(len(RIDDLES))
    await update.message.reply_text(
        riddle_text(i, "Random Riddle"),
        parse_mode="Markdown",
        reply_markup=reveal_keyboard(i),
    )


async def reveal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    i = int(query.data.split(":")[1])
    await query.answer()
    await query.edit_message_text(
        f"{riddle_text(i, 'Riddle')}\n\n✅ *Answer:* {RIDDLES[i]['a']}",
        parse_mode="Markdown",
    )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = load_subs()
    subs.add(update.effective_chat.id)
    save_subs(subs)
    await update.message.reply_text(
        f"✅ Subscribed! You'll get a new riddle every day at {DAILY_HOUR_UTC:02d}:00 UTC."
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = load_subs()
    subs.discard(update.effective_chat.id)
    save_subs(subs)
    await update.message.reply_text("You're unsubscribed. Use /subscribe anytime to come back.")


# ---------- daily job ----------
async def send_daily(context: ContextTypes.DEFAULT_TYPE):
    i = todays_index()
    for chat_id in load_subs():
        try:
            await context.bot.send_message(
                chat_id,
                riddle_text(i, "Riddle of the Day"),
                parse_mode="Markdown",
                reply_markup=reveal_keyboard(i),
            )
        except Exception as e:  # e.g. user blocked the bot
            logging.warning("Could not send to %s: %s", chat_id, e)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("riddle", riddle))
    app.add_handler(CommandHandler("random", random_riddle))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CallbackQueryHandler(reveal, pattern=r"^ans:"))

    app.job_queue.run_daily(send_daily, time=time(DAILY_HOUR_UTC, 0, tzinfo=timezone.utc))
    app.run_polling()


if __name__ == "__main__":
    main()
