import asyncio
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta

# Bot Token
TOKEN = "7992710089:AAG2SS1ZqVupi4qMtMNN_cmvvzpIOnpY-ec"

# Global dictionary to store active timers for each chat
active_timers = {}

# Define string literals for time labels
MONTH_LABEL = "Mon"
DAY_LABEL = "Day"
HOUR_LABEL = "Hou"
MINUTE_LABEL = "Min"
SECOND_LABEL = "Sec"

def format_time(seconds: int) -> str:
    """Format the remaining time into months, days, hours, minutes, and seconds."""
    months = seconds // (3600 * 24 * 30)  # Assuming 30 days in a month
    seconds %= (3600 * 24 * 30)

    days = seconds // (3600 * 24)
    seconds %= (3600 * 24)

    hours = seconds // 3600
    seconds %= 3600

    minutes = seconds // 60
    seconds %= 60

    # Format the time into a structured string with labels
    formatted_time = f"""
    {MONTH_LABEL} : {DAY_LABEL} : {HOUR_LABEL} : {MINUTE_LABEL} : {SECOND_LABEL}
     {months:3d}    {days:5d}     {hours:3d}     {minutes:2d}      {seconds:3d}
    """
    return f"Remaining Time ⏳ \n {formatted_time} \n Left‼️ \n"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    message = (
        "Hi! Use /set <seconds> <title> to start a countdown.\n"
        "Use /stop <title> to stop a specific timer.\n"
        "Use /stopall to stop all timers in this chat.\n"
        "Use /refresh <title> to refresh a specific timer.\n"
        "Use /refreshall to refresh all timers in this chat."
    )
    await update.message.reply_text(message)

async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /set command to start a timer."""
    chat_id = update.effective_chat.id
    try:
        # Parse the total seconds and title
        total_seconds = int(context.args[0])
        title = " ".join(context.args[1:]) if len(context.args) > 1 else "Countdown"

        # Validate input
        if total_seconds < 0:
            await update.message.reply_text("❌ Please provide a non-negative value for seconds.")
            return

        # Stop any existing timer with the same title
        if chat_id in active_timers and title in active_timers[chat_id]:
            active_timers[chat_id][title]["running"] = False

        # Start the timer in a separate task
        await update.message.reply_text(f"✅ Timer '{title}' set for {format_time(total_seconds)}. Live updates will begin shortly.")
        asyncio.create_task(run_timer(chat_id, total_seconds, title, context))

    except (IndexError, ValueError):
        await update.message.reply_text("❗ Usage: /set <seconds> <title>")

async def run_timer(chat_id: int, total_seconds: int, title: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs the countdown timer."""
    start_time = datetime.now()
    remaining_seconds = total_seconds

    # Save the timer reference for this title
    if chat_id not in active_timers:
        active_timers[chat_id] = {}

    active_timers[chat_id][title] = {"running": True, "remaining_seconds": total_seconds, "title": title, "day_decreased": False}

    while remaining_seconds > 0 and active_timers[chat_id][title]["running"]:
        try:
            current_time = datetime.now()
            elapsed_time = current_time - start_time
            remaining_seconds = total_seconds - int(elapsed_time.total_seconds())

            # Update the remaining time and send the notification
            active_timers[chat_id][title]["remaining_seconds"] = remaining_seconds
            remaining_days = remaining_seconds // (3600 * 24)

            # Check if a day has passed and send a notification only once
            if remaining_days < (total_seconds // (3600 * 24)) and not active_timers[chat_id][title]["day_decreased"]:
                active_timers[chat_id][title]["day_decreased"] = True
                await context.bot.send_message(chat_id, f"‼️ A day has passed! {format_time(remaining_seconds)}.")

            # Update the timer message
            timer_message = f"‼️ {title}\n\n{format_time(remaining_seconds)}\n\n_\"The bad news is time flies. The good news is you're the pilot.\"_"

            if "message" not in active_timers[chat_id][title]:
                message = await context.bot.send_message(chat_id, timer_message, parse_mode="Markdown")
                active_timers[chat_id][title]["message"] = message
            else:
                message = active_timers[chat_id][title]["message"]

            try:
                await message.edit_text(timer_message, parse_mode="Markdown")
            except Exception as e:
                print(f"Error updating message: {e}")

            await asyncio.sleep(5)

        except asyncio.CancelledError:
            print("Timer task cancelled")
            break
        except Exception as e:
            print(f"Unexpected error in timer: {e}")

    # Clean up after the timer ends
    if chat_id in active_timers and title in active_timers[chat_id]:
        del active_timers[chat_id][title]

    if remaining_seconds <= 0:
        await context.bot.send_message(chat_id, f"*{title}* has ended!", parse_mode="Markdown")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /stop command to stop a specific timer."""
    chat_id = update.effective_chat.id
    if len(context.args) == 0:
        await update.message.reply_text("⚠️ You must provide a title to stop a specific timer.")
        return

    title = " ".join(context.args)
    if chat_id in active_timers and title in active_timers[chat_id]:
        active_timers[chat_id][title]["running"] = False
        del active_timers[chat_id][title]
        await update.message.reply_text(f"⏹️ Timer '{title}' stopped.")
    else:
        await update.message.reply_text(f"⚠️ No active timer with title '{title}' found.")

async def stopall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /stopall command to stop all timers in the chat."""
    chat_id = update.effective_chat.id
    if chat_id in active_timers:
        for title in list(active_timers[chat_id].keys()):
            active_timers[chat_id][title]["running"] = False
            del active_timers[chat_id][title]
        await update.message.reply_text("⏹️ All timers in this chat have been stopped.")
    else:
        await update.message.reply_text("⚠️ No active timers to stop in this chat.")

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /refresh command to refresh a specific timer."""
    chat_id = update.effective_chat.id
    if len(context.args) == 0:
        await update.message.reply_text("⚠️ You must provide a title to refresh a specific timer.")
        return

    title = " ".join(context.args)
    if chat_id in active_timers and title in active_timers[chat_id]:
        current_timer = active_timers[chat_id][title]
        current_timer["running"] = False

        if "message" in current_timer:
            old_message = current_timer["message"]
            try:
                await old_message.delete()
            except Exception as e:
                print(f"Error deleting old message: {e}")

        del active_timers[chat_id][title]
        await update.message.reply_text(f"♻️ Timer '{title}' for this chat is being refreshed.")

        remaining_seconds = current_timer["remaining_seconds"]
        asyncio.create_task(run_timer(chat_id, remaining_seconds, title, context))
    else:
        await update.message.reply_text(f"⚠️ No active timer with title '{title}' found.")

async def refreshall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /refreshall command to refresh all timers in the chat."""
    chat_id = update.effective_chat.id
    if chat_id in active_timers:
        for title in list(active_timers[chat_id].keys()):
            await refresh(update, context)
        await update.message.reply_text("♻️ All timers in this chat have been refreshed.")
    else:
        await update.message.reply_text("⚠️ No active timers to refresh in this chat.")

def restart_bot():
    """Restart the bot if it crashes or stops."""
    while True:
        try:
            application = Application.builder().token(TOKEN).build()

            # Add command handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("set", set_timer))
            application.add_handler(CommandHandler("stop", stop))
            application.add_handler(CommandHandler("stopall", stopall))
            application.add_handler(CommandHandler("refresh", refresh))
            application.add_handler(CommandHandler("refreshall", refreshall))

            application.run_polling()

        except Exception as e:
            print(f"Bot stopped due to error: {e}")
            print("Restarting the bot...")
            continue  # Restart the bot if it stops

if __name__ == "__main__":
    restart_bot()
