from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

user_links = {} # e.g {user_id: {'linkedin': ..., 'instagram': ...}}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Please send me your LinkedIn profile link.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.fromt_user.id
    text = update.message.text
    if "linkedin.com" in text: # Valid Linkedin Profile
        user_links.setdefault(user_id, {})['linkedin'] = text
        await update.message.reply_text("Got your LinkedIn! Now, please send me your Instagram profile link.")
    elif "instagram.com" in text:
        user_links.setdefault(user_id, {})['instagram'] = text
        await update.message.reply_text("You're all set!")

async def add_me(update: Update, context: ContextTypes.DEAFULT_TYPE):
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    links = user_links.get(user_id)

    if not links:
        await update.callback_query.answer("Please set your links first in a private chat with LinkListBot.")
        return

    context.bot_data.setdefault(chat_id, [])
    context.bot_data[chat_id].append({
        'name': user.full_name,
        'linkedin': links.get('linkedin'),
        'instagram': links.get('instagram')
    })

    message = "👥 Networking Links:\n"
    for i, person in enumerate(context.bot_data[chat_id], 1):
        message += f"{i}. {person['name']} - "
        if person.get('linkedin'):
            message += f"[LinkedIn]({person['linkedin']}) "
        if person.get('instagram'):
            message += f"[Instagram]({person['instagram']})"
        message += "\n"
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Add me (LinkedIn)", callback_data='add_linkedin')],
            [InlineKeyboardButton("📸 Add me (Instagram)", callback_data='add_instagram')],
        ]),
        parse_mode="Markdown"
    )

async def button(update: Update, context: ContextTypes.DEAFULT_TYPE):
    query = update.callback_query
    await query.answer()
    await add_me(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()