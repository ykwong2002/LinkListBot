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
    user_id = str(update.message.from_user.id)
    user_links = get_user_links(user_id) or {}
    
    welcome_text = (
        "👋 Welcome to LinkList Bot!\n\n"
        "I help people share their LinkedIn and Instagram links in group chats.\n\n"
        "🔄 *How it works:*\n"
        "1️⃣ Set up your links in this private chat\n"
        "2️⃣ Add me to any group chat\n"
        "3️⃣ Use /chain in the group to start a link collection\n"
        "4️⃣ Click buttons to add your links to the chain\n\n"
        "Please use the buttons below to manage your links:"
    )
    
    # Show different buttons based on what links are already set
    keyboard = []
    if user_links.get('linkedin'):
        keyboard.append([
            InlineKeyboardButton("✏️ Edit LinkedIn", callback_data='edit_linkedin_btn'),
            InlineKeyboardButton("❌ Remove LinkedIn", callback_data='remove_linkedin_btn')
        ])
    else:
        keyboard.append([InlineKeyboardButton("➕ Add LinkedIn", callback_data='add_linkedin_btn')])
    
    if user_links.get('instagram'):
        keyboard.append([
            InlineKeyboardButton("✏️ Edit Instagram", callback_data='edit_instagram_btn'),
            InlineKeyboardButton("❌ Remove Instagram", callback_data='remove_instagram_btn')
        ])
    else:
        keyboard.append([InlineKeyboardButton("➕ Add Instagram", callback_data='add_instagram_btn')])
    
    # Add help and group instructions
    keyboard.append([InlineKeyboardButton("❓ How to Use", callback_data='help')])
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🔄 *LinkList Bot Help*\n\n"
        "*Step 1:* Set up your links in private chat\n"
        "- Use the buttons to add LinkedIn & Instagram links\n\n"
        "*Step 2:* Add the bot to your group chat\n"
        "- Search for @YourBotUsername and add to group\n\n"
        "*Step 3:* Start a chain in the group\n"
        "- Type /chain in the group chat\n\n"
        "*Step 4:* Add your links to the chain\n"
        "- Click 'Add Me (LinkedIn)' or 'Add Me (Instagram)'\n"
        "- The bot will update the message with everyone's links\n\n"
        "*Additional Commands:*\n"
        "/start - Show the main menu\n"
        "/help - Show this help message\n"
        "/chain - Start a link chain in a group\n"
        "/edit_linkedin - Edit your LinkedIn link\n"
        "/edit_instagram - Edit your Instagram link\n"
        "/remove_linkedin - Remove your LinkedIn link\n"
        "/remove_instagram - Remove your Instagram link"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )

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
        await update.message.reply_text("✅ LinkedIn link saved!")
        
        # Check if the user already has an Instagram link
        user_links = get_user_links(user_id) or {}
        if not user_links.get('instagram'):
            await update.message.reply_text(
                "Would you like to add your Instagram link too?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add Instagram", callback_data='add_instagram_btn')],
                    [InlineKeyboardButton("Skip", callback_data='skip_instagram')]
                ])
            )
        else:
            await show_main_menu(update, context)
            
        context.user_data.pop('awaiting', None)

    elif context.user_data.get('awaiting') == 'instagram' and instagram_pattern.search(text):
        save_user_links(user_id, 'instagram', text)
        await update.message.reply_text("✅ Instagram link saved!")
        
        # Check if the user already has a LinkedIn link
        user_links = get_user_links(user_id) or {}
        if not user_links.get('linkedin'):
            await update.message.reply_text(
                "Would you like to add your LinkedIn link too?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add LinkedIn", callback_data='add_linkedin_btn')],
                    [InlineKeyboardButton("Skip", callback_data='skip_linkedin')]
                ])
            )
        else:
            # Show the success message with instructions for group chat
            await update.message.reply_text(
                "🎉 *All Set!*\n\n"
                "You can now add me to group chats and share your links.\n\n"
                "In any group chat:\n"
                "1️⃣ Add this bot to the group\n"
                "2️⃣ Type /chain to start a link collection\n"
                "3️⃣ Click the buttons to add your links",
                parse_mode='Markdown'
            )
            await show_main_menu(update, context)
            
        context.user_data.pop('awaiting', None)

    elif context.user_data.get('awaiting') == 'linkedin_edit' and linkedin_pattern.search(text):
        save_user_links(user_id, 'linkedin', text)
        await update.message.reply_text("✅ LinkedIn link updated!")
        await show_main_menu(update, context)
        context.user_data.pop('awaiting', None)

    elif context.user_data.get('awaiting') == 'instagram_edit' and instagram_pattern.search(text):
        save_user_links(user_id, 'instagram', text)
        await update.message.reply_text("✅ Instagram link updated!")
        await show_main_menu(update, context)
        context.user_data.pop('awaiting', None)

    else:
        await update.message.reply_text(
            "Please send a valid link (LinkedIn or Instagram).\n\n"
            "LinkedIn format: linkedin.com/in/username\n"
            "Instagram format: instagram.com/username"
        )

async def start_chain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if this is a group chat
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "❗ This command only works in group chats.\n\n"
            "Add me to a group and run /chain there!"
        )
        return
        
    intro_text = (
        "👥 *Networking Links*\n\n"
        "Click the buttons below to add your links to this list.\n"
        "Make sure you've already set up your links in a private chat with me first!\n\n"
        "Need help? Type /help or message me privately."
    )
    
    keyboard = [
        [InlineKeyboardButton("🔗 Add Me (LinkedIn)", callback_data='add_linkedin')],
        [InlineKeyboardButton("📸 Add Me (Instagram)", callback_data='add_instagram')],
        [InlineKeyboardButton("❌ Remove Me", callback_data='remove_me')]
    ]
    await update.message.reply_text(
        intro_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Helper function to show the main menu in private chat"""
    user_id = str(update.effective_user.id)
    user_links = get_user_links(user_id) or {}
    
    welcome_text = (
        "👋 *LinkList Bot Menu*\n\n"
        "Please use the buttons below to manage your links:"
    )
    
    # Show different buttons based on what links are already set
    keyboard = []
    if user_links.get('linkedin'):
        keyboard.append([
            InlineKeyboardButton("✏️ Edit LinkedIn", callback_data='edit_linkedin_btn'),
            InlineKeyboardButton("❌ Remove LinkedIn", callback_data='remove_linkedin_btn')
        ])
    else:
        keyboard.append([InlineKeyboardButton("➕ Add LinkedIn", callback_data='add_linkedin_btn')])
    
    if user_links.get('instagram'):
        keyboard.append([
            InlineKeyboardButton("✏️ Edit Instagram", callback_data='edit_instagram_btn'),
            InlineKeyboardButton("❌ Remove Instagram", callback_data='remove_instagram_btn')
        ])
    else:
        keyboard.append([InlineKeyboardButton("➕ Add Instagram", callback_data='add_instagram_btn')])
    
    # Add help and group instructions
    keyboard.append([InlineKeyboardButton("❓ How to Use", callback_data='help')])
    
    await update.effective_message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = str(user.id)
    
    # Handle private chat buttons
    if query.data in ['add_linkedin_btn', 'edit_linkedin_btn', 'add_instagram_btn', 'edit_instagram_btn', 
                      'remove_linkedin_btn', 'remove_instagram_btn', 'help', 'skip_linkedin', 'skip_instagram']:
        if query.data == 'add_linkedin_btn' or query.data == 'edit_linkedin_btn':
            await query.message.reply_text("Please send your LinkedIn profile link:")
            context.user_data['awaiting'] = 'linkedin'
            return
            
        elif query.data == 'add_instagram_btn' or query.data == 'edit_instagram_btn':
            await query.message.reply_text("Please send your Instagram profile link:")
            context.user_data['awaiting'] = 'instagram'
            return
            
        elif query.data == 'remove_linkedin_btn':
            links = get_user_links(user_id) or {}
            if 'linkedin' in links:
                links.pop('linkedin')
                save_user_links(user_id, 'linkedin', None)
                await query.message.reply_text("✅ LinkedIn link removed.")
            else:
                await query.message.reply_text("No LinkedIn link found.")
            # Show the main menu again
            await show_main_menu(update, context)
            return
            
        elif query.data == 'remove_instagram_btn':
            links = get_user_links(user_id) or {}
            if 'instagram' in links:
                links.pop('instagram')
                save_user_links(user_id, 'instagram', None)
                await query.message.reply_text("✅ Instagram link removed.")
            else:
                await query.message.reply_text("No Instagram link found.")
            # Show the main menu again
            await show_main_menu(update, context)
            return
        
        elif query.data == 'skip_linkedin' or query.data == 'skip_instagram':
            # Show success message and instructions for group
            await query.message.reply_text(
                "🎉 *All Set!*\n\n"
                "You can now add me to group chats and share your links.\n\n"
                "In any group chat:\n"
                "1️⃣ Add this bot to the group\n"
                "2️⃣ Type /chain to start a link collection\n"
                "3️⃣ Click the buttons to add your links",
                parse_mode='Markdown'
            )
            await show_main_menu(update, context)
            return
            
        elif query.data == 'help':
            await help_command(update, context)
            return
    
    # For group chats, continue with existing functionality
    chat_id = str(query.message.chat.id)
    
    if query.data == 'remove_me':
        # Remove user from group
        members = get_group_users(chat_id)
        if user_id in members:
            members.remove(user_id)
            db.reference(f'groups/{chat_id}').set(members)
        
        # Remove user contributions in this group
        db.reference(f'group_contributions/{chat_id}/{user_id}').delete()
        
        # Update chain message
        group_user_ids = get_group_users(chat_id)
        text = "👥 Networking Links:\n"
        for idx, uid in enumerate(group_user_ids, 1):
            info = get_user_links(uid)
            user_contributions = db.reference(f'group_contributions/{chat_id}/{uid}').get() or {}
            name = (await context.bot.get_chat(uid)).full_name
            entry = f"{idx}. {name}"
            
            has_link = False
            if user_contributions.get('linkedin') and info.get('linkedin'):
                entry += f" – [LinkedIn]({info['linkedin']})"
                has_link = True
            
            if user_contributions.get('instagram') and info.get('instagram'):
                if has_link:
                    entry += f" | [Instagram]({info['instagram']})"
                else:
                    entry += f" – [Instagram]({info['instagram']})"
            
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
    platform = None
    
    # Determine which platform the user clicked
    if query.data == 'add_linkedin':
        platform = 'linkedin'
        if not links or not links.get(platform):
            # Guide the user to set up their link first
            await query.message.reply_text(
                "❗ You haven't set your LinkedIn link yet!\n\n"
                "1️⃣ Start a private chat with me: @YourBotUsername\n"
                "2️⃣ Use the Add LinkedIn button to set your link\n"
                "3️⃣ Then come back to the group and try again"
            )
            return
    elif query.data == 'add_instagram':
        platform = 'instagram'
        if not links or not links.get(platform):
            # Guide the user to set up their link first
            await query.message.reply_text(
                "❗ You haven't set your Instagram link yet!\n\n"
                "1️⃣ Start a private chat with me: @YourBotUsername\n"
                "2️⃣ Use the Add Instagram button to set your link\n"
                "3️⃣ Then come back to the group and try again"
            )
            return
    
    # Track user contributions in the group
    ref = db.reference(f'group_contributions/{chat_id}/{user_id}')
    contributions = ref.get() or {}
    contributions[platform] = True
    ref.set(contributions)
    
    # Save user to group if not already present
    save_group_user(chat_id, user_id)
    group_user_ids = get_group_users(chat_id)

    # Compile new message
    text = "👥 Networking Links:\n"
    for idx, uid in enumerate(group_user_ids, 1):
        info = get_user_links(uid)
        user_contributions = db.reference(f'group_contributions/{chat_id}/{uid}').get() or {}
        name = (await context.bot.get_chat(uid)).full_name
        entry = f"{idx}. {name}"
        
        has_link = False
        if user_contributions.get('linkedin') and info.get('linkedin'):
            entry += f" – [LinkedIn]({info['linkedin']})"
            has_link = True
        
        if user_contributions.get('instagram') and info.get('instagram'):
            if has_link:
                entry += f" | [Instagram]({info['instagram']})"
            else:
                entry += f" – [Instagram]({info['instagram']})"
        
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
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("chain", start_chain))
    app.add_handler(CommandHandler("edit_linkedin", edit_linkedin))
    app.add_handler(CommandHandler("edit_instagram", edit_instagram))
    app.add_handler(CommandHandler("remove_linkedin", remove_linkedin))
    app.add_handler(CommandHandler("remove_instagram", remove_instagram))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot is running...")
    app.run_polling()