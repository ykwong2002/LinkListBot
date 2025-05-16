import os
import logging
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import re

# Load environment details
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Firebase setup
import firebase_admin
from firebase_admin import credentials, db

# Load Firebase credentials from environment variable (recommended for Render)
service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
cred = credentials.Certificate(service_account_info)
# You must set FIREBASE_DATABASE_URL in your environment variables (Render dashboard)
db_url = os.getenv("FIREBASE_DATABASE_URL")
firebase_admin.initialize_app(cred, {
    'databaseURL': db_url
})

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
        "👋 Welcome to LinkList Bot!\nPlease send me your LinkedIn link:"
    )
    context.user_data['awaiting'] = 'linkedin'

async def edit_linkedin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your new LinkedIn link:")
    context.user_data['awaiting'] = 'linkedin_edit'

async def edit_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your new Instagram link:")
    context.user_data['awaiting'] = 'instagram_edit'

async def remove_linkedin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    links = get_user_links(user_id) or {}
    if 'linkedin' in links:
        links.pop('linkedin')
        save_user_links(user_id, 'linkedin', None)
        await update.message.reply_text("✅ LinkedIn link removed.")
    else:
        await update.message.reply_text("No LinkedIn link found.")

async def remove_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    links = get_user_links(user_id) or {}
    if 'instagram' in links:
        links.pop('instagram')
        save_user_links(user_id, 'instagram', None)
        await update.message.reply_text("✅ Instagram link removed.")
    else:
        await update.message.reply_text("No Instagram link found.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip()

    linkedin_pattern = re.compile(r"linkedin\.com/(in|pub|company)/[\w\-]+", re.IGNORECASE)
    instagram_pattern = re.compile(r"instagram\.com/([\w\.]+)", re.IGNORECASE)

    if context.user_data.get('awaiting') == 'linkedin' and linkedin_pattern.search(text):
        save_user_links(user_id, 'linkedin', text)
        await update.message.reply_text("✅ LinkedIn saved! Now send your Instagram link.")
        context.user_data['awaiting'] = 'instagram'

    elif context.user_data.get('awaiting') == 'instagram' and instagram_pattern.search(text):
        save_user_links(user_id, 'instagram', text)
        await update.message.reply_text("✅ Instagram saved! You're all set! 🎉")
        context.user_data.pop('awaiting', None)

    elif context.user_data.get('awaiting') == 'linkedin_edit' and linkedin_pattern.search(text):
        save_user_links(user_id, 'linkedin', text)
        await update.message.reply_text("✅ LinkedIn link updated!")
        context.user_data.pop('awaiting', None)

    elif context.user_data.get('awaiting') == 'instagram_edit' and instagram_pattern.search(text):
        save_user_links(user_id, 'instagram', text)
        await update.message.reply_text("✅ Instagram link updated!")
        context.user_data.pop('awaiting', None)

    else:
        await update.message.reply_text("Please send a valid link (LinkedIn or Instagram).")

async def start_chain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔗 Add Me (LinkedIn)", callback_data='add_linkedin')],
        [InlineKeyboardButton("📸 Add Me (Instagram)", callback_data='add_instagram')],
        [InlineKeyboardButton("❌ Remove Me", callback_data='remove_me')]
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

    if query.data == 'remove_me':
        # Remove user from group
        members = get_group_users(chat_id)
        if user_id in members:
            members.remove(user_id)
            db.reference(f'groups/{chat_id}').set(members)
        # Update chain message
        group_user_ids = get_group_users(chat_id)
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
            [InlineKeyboardButton("📸 Add Me (Instagram)", callback_data='add_instagram')],
            [InlineKeyboardButton("❌ Remove Me", callback_data='remove_me')]
        ]
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        await query.message.reply_text("You have been removed from the chain.")
        return

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
        [InlineKeyboardButton("📸 Add Me (Instagram)", callback_data='add_instagram')],
        [InlineKeyboardButton("❌ Remove Me", callback_data='remove_me')]
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
    app.add_handler(CommandHandler("edit_linkedin", edit_linkedin))
    app.add_handler(CommandHandler("edit_instagram", edit_instagram))
    app.add_handler(CommandHandler("remove_linkedin", remove_linkedin))
    app.add_handler(CommandHandler("remove_instagram", remove_instagram))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot is running...")
    app.run_polling()