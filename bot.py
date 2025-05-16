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
# You must set FIREBASE_DATABASE_URL in your environment variables (Railway dashboard)
db_url = os.getenv("FIREBASE_DATABASE_URL")
firebase_admin.initialize_app(cred, {
    'databaseURL': db_url
})

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ------------- User Data Logic (endpoint for individual users) -------------
def save_user_links(user_id: str, platform: str, link: str):
    ref = db.reference(f'users/{user_id}')
    ref.update({platform: link})

def get_user_links(user_id: str):
    return db.reference(f'users/{user_id}').get()

# ------------- Group Message Logic (endpoints for group messages) -------------
def save_group_user(chat_id: str, user_id: str):
    ref = db.reference(f'groups/{chat_id}')
    members = ref.get() or []
    if user_id not in members:
        members.append(user_id)
        ref.set(members)

def get_group_users(chat_id: str):
    return db.reference(f'groups/{chat_id}').get() or []

# Track active chain messages in groups
def save_active_chain(chat_id: str, message_id: int):
    # Deactivate previous chain if it exists
    previous_chain = db.reference(f'active_chains/{chat_id}').get()
    
    # Save new active chain
    db.reference(f'active_chains/{chat_id}').set(message_id)
    
    # Return the previous chain id if there was one
    return previous_chain

def get_active_chain(chat_id: str):
    return db.reference(f'active_chains/{chat_id}').get()

# ------------- Telegram Handlers -------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if this is a group chat
    if update.effective_chat.type in ['group', 'supergroup']:
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hi {user.first_name}!\n\n"
            "⚠️ *You need to set up your links privately first*\n\n"
            "👇 *Click this button to start a private chat with me:*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ SET UP MY LINKS", url=f"https://t.me/linklistbot_bot?start=from_group")]
            ]),
            parse_mode='Markdown'
        )
        return
        
    user_id = str(update.message.from_user.id)
    user_links = get_user_links(user_id) or {}
    
    # Check if user was redirected from a group chat
    from_group = False
    if context.args and context.args[0] == "from_group":
        from_group = True
    
    welcome_text = (
        "👋 *Welcome to LinkList Bot!*\n\n"
    )
    
    # Add specific text for users coming from a group
    if from_group:
        welcome_text += (
            "Thanks for clicking through from the group! Let's set up your links first.\n\n"
        )
    
    welcome_text += (
        "I make it easy for groups to share LinkedIn and Instagram links through a single, clean chain message — perfect for *networking events*, *orientation camps*, or *project teams*.\n\n"
        "🌟 *What makes me different?*\n"
        "You only need to set up your LinkedIn and Instagram *once* in this private chat — after that, adding yourself to the chain in *any* group takes just *one tap* 👉📲.\n\n"
        "🔄 *How it works:*\n"
        "1️⃣ Set up your links below\n"
        "2️⃣ Add me to any group chat\n"
        "3️⃣ Use /chain in the group to start a link list\n"
        "4️⃣ Tap the button to instantly add yourself\n\n"
        "✅ No need to retype usernames or copy-paste links\n"
        "✅ Just click others' names to open their profiles directly\n\n"
        "Ready to connect smarter? Use the buttons below to set up your links:"
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
    
    # Add help and group instructions (currently not functional)
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
        "- Search for @linklistbot_bot and add to group\n\n"
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
    await update.message.reply_text(
        "Please send your new Instagram profile link or just your username (e.g., @username):"
    )
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
    instagram_username_pattern = re.compile(r"^@([\w\.]+)$")

    if context.user_data.get('awaiting') == 'linkedin' and linkedin_pattern.search(text):
        save_user_links(user_id, 'linkedin', text)
        await update.message.reply_text("✅ LinkedIn link saved!")
        
        # Check if the user already has an Instagram link
        user_links = get_user_links(user_id) or {}
        if not user_links.get('instagram'):
            await update.message.reply_text(
                "Would you like to add your Instagram link too?\n"
                "You can simply send your username as @username",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add Instagram", callback_data='add_instagram_btn')],
                    [InlineKeyboardButton("Skip", callback_data='skip_instagram')]
                ])
            )
        else:
            await show_main_menu(update, context)
            
        context.user_data.pop('awaiting', None)

    elif context.user_data.get('awaiting') == 'instagram':
        # Check if it's an @username format
        username_match = instagram_username_pattern.match(text)
        if username_match:
            # Convert @username to a proper Instagram link
            username = username_match.group(1)
            instagram_link = f"https://instagram.com/{username}"
            save_user_links(user_id, 'instagram', instagram_link)
            await update.message.reply_text("✅ Instagram link saved!")
        elif instagram_pattern.search(text):
            # It's already a proper Instagram link, so no need for reformatting
            save_user_links(user_id, 'instagram', text)
            await update.message.reply_text("✅ Instagram link saved!")
        else:
            # Invalid format of Instagram
            await update.message.reply_text(
                "Please send a valid Instagram username (@username) or link (instagram.com/username)."
            )
            return
        
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
            # Show the success message with instructions for group chat --> redirection to group chat
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

    elif context.user_data.get('awaiting') == 'instagram_edit':
        # Check if it's an @username format
        username_match = instagram_username_pattern.match(text)
        if username_match:
            # Convert @username to a proper Instagram link
            username = username_match.group(1)
            instagram_link = f"https://instagram.com/{username}"
            save_user_links(user_id, 'instagram', instagram_link)
            await update.message.reply_text("✅ Instagram link updated!")
            await show_main_menu(update, context)
            context.user_data.pop('awaiting', None)
        elif instagram_pattern.search(text):
            # It's already a proper Instagram link
            save_user_links(user_id, 'instagram', text)
            await update.message.reply_text("✅ Instagram link updated!")
            await show_main_menu(update, context)
            context.user_data.pop('awaiting', None)
        else:
            # Invalid format
            await update.message.reply_text(
                "Please send a valid Instagram username (@username) or link (instagram.com/username)."
            )

    else:
        await update.message.reply_text(
            "Please send a valid link or username.\n\n"
            "LinkedIn format: linkedin.com/in/username\n"
            "Instagram format: @username or instagram.com/username"
        )
# Initialize the networking chain in the group chat
async def start_chain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if this is a group chat
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "❗ This command only works in group chats.\n\n"
            "Add me to a group and run /chain there!"
        )
        return
    
    # Get the user who initiated the chain
    user_id = str(update.effective_user.id)
    user_links = get_user_links(user_id) or {}
    
    # Check if the user has set up any links
    if not user_links or (not user_links.get('linkedin') and not user_links.get('instagram')):
        # Send detailed instructions to private chat only - no message in group
        user = update.effective_user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"👋 Hi {user.first_name}!\n\n"
                "⚠️ *You need to set up your links privately first*\n\n"
                "👇 *Please use the buttons below to set up your links:*",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add LinkedIn", callback_data='add_linkedin_btn')],
                    [InlineKeyboardButton("➕ Add Instagram", callback_data='add_instagram_btn')]
                ]),
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error sending private message: {e}")
            # If sending private message fails, send message in group
            await update.message.reply_text(
                f"👋 Hi {user.first_name}!\n\n"
                "You need to start a private chat with me first to set up your links.\n\n"
                "👇 Click the button below to set up your links:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ SET UP MY LINKS", url=f"https://t.me/linklistbot_bot?start=from_group")]
                ])
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
    
    # Send the new chain message
    chain_message = await update.message.reply_text(
        intro_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    # Get previous active chain message and deactivate it
    chat_id = str(update.effective_chat.id)
    previous_chain_id = save_active_chain(chat_id, chain_message.message_id)
    
    # If there was a previous chain, update it to remove interactive buttons (ARCHIIVE to prevent confusion)
    if previous_chain_id:
        try:
            # Get all participants from the current active chain's contributions
            group_user_ids = get_group_users(chat_id)
            text = "👥 Networking Links *(ARCHIVED)*:\n"
            for idx, uid in enumerate(group_user_ids, 1):
                info = get_user_links(uid)
                user_contributions = db.reference(f'group_contributions/{chat_id}/{uid}').get() or {}
                try:
                    name = (await context.bot.get_chat(uid)).full_name
                except:
                    name = "User"
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
            
            # Update the previous chain message to remove buttons and mark as archived
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=previous_chain_id,
                text=text + "\n\n*A new chain has been started. This one is no longer active.*",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error updating previous chain: {e}")

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
            await query.message.reply_text(
                "Please send your Instagram profile link or just your username (e.g., @username):"
            )
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
            help_text = (
                "🔄 *LinkList Bot Help*\n\n"
                "*Step 1:* Set up your links in private chat\n"
                "- Use the buttons to add LinkedIn & Instagram links\n\n"
                "*Step 2:* Add the bot to your group chat\n"
                "- Search for @linklistbot_bot and add to group\n\n"
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
            
            await query.message.reply_text(
                help_text,
                parse_mode='Markdown'
            )
            return
    
    # For group chats
    chat_id = str(query.message.chat.id)
    message_id = query.message.message_id
    
    # Check if this is the active chain message, redirect to lowest message (most recent)
    active_chain_id = get_active_chain(chat_id)
    if active_chain_id != message_id:
        await query.message.reply_text(
            "⚠️ This chain is no longer active. Please use the most recent chain message.",
            reply_to_message_id=message_id
        )
        return
    
    if query.data == 'remove_me':
        # Remove user from group in realtime DB
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
        
        # Send confirmation to the user's private chat instead of the group (prevent spamming)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ You have been removed from the networking chain in {query.message.chat.title}."
            )
        except Exception as e:
            logging.error(f"Error sending private message: {e}")
            
        return

    links = get_user_links(user_id)
    platform = None
    
    # Determine which platform the user clicked
    if query.data == 'add_linkedin':
        platform = 'linkedin'
        if not links or not links.get(platform):
            # Guide the user to set up their link first, but in private chat
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❗ You haven't set your LinkedIn link yet!\n\n"
                    "Please use the button below to set up your LinkedIn link:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Add LinkedIn", callback_data='add_linkedin_btn')]
                    ])
                )
            except Exception as e:
                logging.error(f"Error sending private message: {e}")
                # Only if private message fails, send message in group
                await query.message.reply_text(
                    "❗ You need to set up your LinkedIn link first. Please start a private chat with me."
                )
            return
    elif query.data == 'add_instagram':
        platform = 'instagram'
        if not links or not links.get(platform):
            # Guide the user to set up their link first, but in private chat
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❗ You haven't set your Instagram link yet!\n\n"
                    "Please use the button below to set up your Instagram link, or simply send me your username as @username:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Add Instagram", callback_data='add_instagram_btn')]
                    ])
                )
            except Exception as e:
                logging.error(f"Error sending private message: {e}")
                # Only if private message fails, send message in group
                await query.message.reply_text(
                    "❗ You need to set up your Instagram link first. Please start a private chat with me."
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