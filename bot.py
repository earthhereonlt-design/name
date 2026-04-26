import os
import asyncio
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from generator import generate_usernames, PATTERN_REGEX
from checker import check_username, CheckStatus, get_stealth_delay

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

# Global state for bot
is_running = False
is_manual_running = False
uptime_start = time.time()
total_checks = 0
total_taken = 0
found_available = []
aadi_available = []
sarcastic_available = []
results_message = None
current_batch = 0
current_batch_index = 0
current_batch_size = 0
manual_queue = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Instagram Discovery Bot is ready. Use /run to start, /stop to halt, /check <user> to check manually, /health for status.")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = time.time() - uptime_start
    m, s = divmod(int(uptime), 60)
    h, m = divmod(m, 60)
    
    batch_info = ""
    if is_running:
        remaining_checks = current_batch_size - current_batch_index
        # Rough estimate based on average expected delay (e.g. 15s)
        estimated_seconds_left = remaining_checks * 15
        em, es = divmod(int(estimated_seconds_left), 60)
        batch_info = f"\nCurrent Batch: {current_batch}\nBatch Progress: {current_batch_index}/{current_batch_size}\nEst. Batch Time Left: ~{em}m {es}s"
    
    mq_str = f"\nManual Queue: {len(manual_queue)}" if manual_queue else ""

    status_msg = (
        f"📊 Bot Health\n"
        f"Status: {'Running 🟢' if is_running else 'Stopped 🔴'}\n"
        f"Uptime: {h}h {m}m {s}s\n"
        f"Total Checks: {total_checks}\n"
        f"❌ Taken: {total_taken}\n"
        f"✨ Found: {len(found_available)}{batch_info}{mq_str}"
    )
    await update.message.reply_text(status_msg)

async def run_manual_checks(bot):
    global is_manual_running, total_checks, total_taken, found_available, is_running, aadi_available, sarcastic_available
    if is_manual_running or is_running:
        return
    is_manual_running = True
    try:
        while manual_queue and not is_running: 
            man_u, chat_id = manual_queue.pop(0)
            await bot.send_message(chat_id=chat_id, text=f"Checking manual target: {man_u}...")
            result = await asyncio.to_thread(check_username, man_u)
            total_checks += 1
            if result.status == CheckStatus.AVAILABLE:
                if man_u not in (aadi_available + sarcastic_available):
                    if PATTERN_REGEX.match(man_u):
                        aadi_available.append(man_u)
                    else:
                        sarcastic_available.append(man_u)
                    found_available.append(man_u)
                    await update_results(bot, chat_id)
                await bot.send_message(chat_id=chat_id, text=f"✅ MANUAL AVAILABLE: {man_u}")
            elif result.status == CheckStatus.TAKEN:
                total_taken += 1
                await bot.send_message(chat_id=chat_id, text=f"❌ MANUAL TAKEN: {man_u}")
            elif result.status == CheckStatus.BANNED:
                wait_time = 300
                await bot.send_message(chat_id=chat_id, text=f"🚨 IP BLOCK DETECTED! Waiting {wait_time}s before automatic retry...")
                await asyncio.sleep(wait_time)
                # Put the username back at the start of the queue to retry it
                manual_queue.insert(0, (man_u, chat_id))
                continue
            else:
                await bot.send_message(chat_id=chat_id, text=f"⚠️ MANUAL {result.status.name}: {man_u} (Manual review recommended)")
            
            if manual_queue and not is_running:
                delay = get_stealth_delay(total_checks)
                await asyncio.sleep(delay)
    except Exception as e:
        print(f"Error in manual check: {e}")
    finally:
        is_manual_running = False

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /check <username>")
        return
    username = context.args[0]
    manual_queue.append((username, update.effective_chat.id))
    position = len(manual_queue)
    if is_running:
        await update.message.reply_text(f"Added {username} to the manual check queue. Position: {position}. Will be checked during next cycle.")
    else:
        await update.message.reply_text(f"Added {username} to the manual check queue. Position: {position}. Checking soon.")
        asyncio.create_task(run_manual_checks(context.bot))

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running
    if is_running:
        is_running = False
        await update.message.reply_text("Stopping after the current batch finishes...")
    else:
        await update.message.reply_text("Bot is already stopped.")

async def update_results(bot, chat_id):
    global results_message, aadi_available, sarcastic_available
    
    aadi_list = "\n".join([f"<code>{u}</code>" for u in aadi_available]) if aadi_available else "<i>None yet</i>"
    sarcastic_list = "\n".join([f"<code>{u}</code>" for u in sarcastic_available]) if sarcastic_available else "<i>None yet</i>"
    
    text = (
        f"✨ <b>Available Usernames</b> ✨\n\n"
        f"<b>Category: Aadi/Adi</b>\n"
        f"{aadi_list}\n\n"
        f"<b>Category: Sarcastic</b>\n"
        f"{sarcastic_list}\n\n"
        f"<i>Click on a username to copy it!</i>"
    )
    
    if results_message is None:
        results_message = await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    else:
        try:
            await results_message.edit_text(text=text, parse_mode='HTML')
        except Exception:
            # If message was deleted or failed to edit
            results_message = await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')

async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, total_checks, total_taken, current_batch, current_batch_index, current_batch_size, aadi_available, sarcastic_available, results_message
    
    if is_running:
        await update.message.reply_text("Bot is already running.")
        return
        
    is_running = True
    current_batch = 0
    batch_usernames = []
    pattern_checks_since_sarcastic = 0
    generation_mode = "pattern"
    
    # Reset findings for new run
    aadi_available = []
    sarcastic_available = []
    results_message = None
    
    status_message = None
    
    try:
        while is_running:
            target_username = None
            is_manual = False
            chat_id = update.effective_chat.id
            
            # 1. Prioritize manual queue
            if manual_queue:
                target_username, chat_id = manual_queue.pop(0)
                is_manual = True
            else:
                # 2. Check if we need a new batch
                if not batch_usernames:
                    current_batch += 1
                    
                    if pattern_checks_since_sarcastic >= 100:
                        generation_mode = "sarcastic"
                    else:
                        generation_mode = "pattern"
                        
                    # Less spam: only show batch start if we've checked some
                    batch_usernames = await asyncio.to_thread(generate_usernames, 25, generation_mode)
                    current_batch_size = len(batch_usernames)
                    current_batch_index = 0
                    
                    if generation_mode == "sarcastic":
                        pattern_checks_since_sarcastic = 0
                
                # Double-check in case generation failed
                if not batch_usernames:
                    await asyncio.sleep(10)
                    continue
                    
                target_username = batch_usernames.pop(0)
                current_batch_index += 1
            
            # Update/Send status message before check
            status_text = (
                f"👤 Checking: {target_username}\n\n"
                f"📊 Stats:\n"
                f"✅ Checked: {total_checks}\n"
                f"❌ Taken: {total_taken}\n"
                f"✨ Found: {len(found_available)}\n\n"
                f"⏳ Still searching..."
            )
            
            if status_message is None:
                status_message = await context.bot.send_message(chat_id=chat_id, text=status_text)
            else:
                try:
                    await status_message.edit_text(status_text)
                except Exception:
                    # Message might be too old or deleted, send a new one
                    status_message = await context.bot.send_message(chat_id=chat_id, text=status_text)

            # Perform check in thread pool
            result = await asyncio.to_thread(check_username, target_username)
            total_checks += 1
            
            # Handle results
            if result.status == CheckStatus.AVAILABLE:
                if target_username not in (aadi_available + sarcastic_available):
                    if PATTERN_REGEX.match(target_username):
                        aadi_available.append(target_username)
                    else:
                        sarcastic_available.append(target_username)
                    
                    found_available.append(target_username) # keep for health stats
                    await update_results(context.bot, chat_id)
                
                prefix = "✅ MANUAL AVAILABLE:" if is_manual else "✅ AVAILABLE:"
                await context.bot.send_message(chat_id=chat_id, text=f"{prefix} {target_username}")
                
            elif result.status == CheckStatus.TAKEN:
                total_taken += 1
                if is_manual:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ MANUAL TAKEN: {target_username}")
                # Automated runs are silent on TAKEN to prevent spam
                
            elif result.status == CheckStatus.UNSURE:
                if is_manual:
                    await context.bot.send_message(chat_id=chat_id, text=f"⚠️ MANUAL UNSURE: {target_username} (Manual review recommended)")
                else:
                    total_taken += 1 # Silent increment
                
            elif result.status == CheckStatus.BANNED:
                wait_time = 300 # 5 minutes
                await context.bot.send_message(chat_id=chat_id, text=f"🚨 IP BLOCK DETECTED! Waiting {wait_time}s before automatic retry...")
                # Re-add to the front of appropriate queue for retry
                if is_manual:
                    manual_queue.insert(0, (target_username, chat_id))
                else:
                    batch_usernames.insert(0, target_username)
                    current_batch_index -= 1 # adjust progress
                
                await asyncio.sleep(wait_time)
                continue
                
            # Update mode tracker
            if not is_manual and generation_mode == "pattern":
                pattern_checks_since_sarcastic += 1
            
            # Stealth delay (only if continuing)
            if is_running:
                delay = get_stealth_delay(total_checks)
                await asyncio.sleep(delay)
            
        # Run finished/stopped
        summary = f"🏁 Run completed or stopped.\nTotal checked this run: {total_checks}\nAvailable names: {len(found_available)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=summary)
        
    except Exception as e:
        is_running = False
        await update.message.reply_text(f"🛑 Error occurred: {str(e)}")

def build_app():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("health", health))
    return app
