import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Load environment details
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Firebase setup
import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ------------- User Data Logic -------------
def save_user_links(user_id: str, platform: str, link: str):
    ref = db.reference(f'users/{user_id}')
    ref.update({platform: link})

def get_user_links(user_id: str):
    return db.reference(f'users/{user_id}').get()

# ------------- Group Message Logic -------------
def save_group_user(chat_id: str, user_id: str):
    ref = db.reference(f'groups/{chat_id}')
    members = ref.get() or []
    if user_id not in members:
        members.append(user_id)
        ref.set(members)

def get_group_users(chat_id: str):
    return db.reference(f'groups/{chat_id}').get() or []

# ------------- Telegram Handlers -------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to LinkUp Bot!\nPlease send me your LinkedIn link:"
    )
    context.user_data['awaiting'] = 'linkedin'

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if context.user_data.get('awaiting') == 'linkedin' and "linkedin.com" in text:
        save_user_links(user_id, 'linkedin', text)
        await update.message.reply_text("✅ LinkedIn saved! Now send your Instagram link.")
        context.user_data['awaiting'] = 'instagram'

    elif context.user_data.get('awaiting') == 'instagram' and "instagram.com" in text:
        save_user_links(user_id, 'instagram', text)
        await update.message.reply_text("✅ Instagram saved! You're all set! 🎉")
        context.user_data.pop('awaiting', None)

    else:
        await update.message.reply_text("Please send a valid link (LinkedIn or Instagram).")

async def start_chain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔗 Add Me (LinkedIn)", callback_data='add_linkedin')],
        [InlineKeyboardButton("📸 Add Me (Instagram)", callback_data='add_instagram')]
    ]
    await update.message.reply_text(
        "👥 Networking Links:\n(Click to join the chain)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = str(user.id)
    chat_id = str(query.message.chat.id)

    links = get_user_links(user_id)
    if not links:
        await query.message.reply_text("❗ Please start a private chat with me and send your LinkedIn/Instagram links first.")
        return

    # Save user to group
    save_group_user(chat_id, user_id)
    group_user_ids = get_group_users(chat_id)

    # Compile new message
    text = "👥 Networking Links:\n"
    for idx, uid in enumerate(group_user_ids, 1):
        info = get_user_links(uid)
        name = (await context.bot.get_chat(uid)).full_name
        entry = f"{idx}. {name} – "

        if info.get('linkedin'):
            entry += f"[LinkedIn]({info['linkedin']}) "
        if info.get('instagram'):
            entry += f"| [Instagram]({info['instagram']})"

        text += entry + "\n"

    keyboard = [
        [InlineKeyboardButton("🔗 Add Me (LinkedIn)", callback_data='add_linkedin')],
        [InlineKeyboardButton("📸 Add Me (Instagram)", callback_data='add_instagram')]
    ]
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ------------- Main -------------
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chain", start_chain))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot is running...")
    app.run_polling()