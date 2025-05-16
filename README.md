# 🤖 LinkListBot

A Telegram bot that simplifies networking in group chats by compiling LinkedIn and Instagram links into a single, organized chain message. Perfect for networking events, orientation camps, and professional group chats.

---

## 🔗 Features

- 📎 **One-tap sharing**: Users click a button to instantly add their social links to the chain.
- 🧠 **Set once, use anywhere**: Links are configured privately and can be used in any group.
- 💬 **Smart chain messaging**: All profiles are compiled into a clean, interactive message.
- 🔄 **Single active chain**: Only the most recent chain remains interactive, preventing confusion.
- 🔒 **Private setup**: Users set up their links in a private chat for security and privacy.
- 🌐 **Works in any Telegram group**: Just add the bot and type `/chain` to start networking.

---

## 🚀 How It Works

1. **Private Setup**: Users set up their LinkedIn and Instagram links in a private chat with the bot.
2. **Group Integration**: Add the bot to any group chat.
3. **Start Chain**: Type `/chain` to create a networking links list.
4. **One-Tap Adding**: Users click buttons to add their LinkedIn or Instagram profiles.
5. **Instant Updates**: The chain message updates instantly with formatted, clickable links.

---

## 🛠️ Tech Stack

- **Language**: Python  
- **Bot Framework**: [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot)  
- **Storage**: Firebase Realtime Database for persistent data storage
- **Hosting**: Compatible with Render or other hosting platforms
- **Environment**: Configured via environment variables with `python-dotenv`

---

## 📦 Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/yourusername/LinkListBot.git
cd LinkListBot
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

---

## 🔐 Configuration

You need to set up the following environment variables:

```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
FIREBASE_DATABASE_URL=your-firebase-database-url
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...} # Your Firebase service account JSON as string
```

1. Get a Telegram bot token by creating a bot via [@BotFather](https://t.me/BotFather) on Telegram.
2. Create a Firebase project and set up a Realtime Database.
3. Generate a service account key in Firebase and format it as a JSON string.

---

## ▶️ Run the Bot

```bash
python bot.py
```

The bot will start polling for updates. For 24/7 deployment, use a hosting platform like Render.

---

## 🧪 User Guide

### For Users

1. **Start a private chat** with the bot:
   - Send `/start` to begin setup
   - Add your LinkedIn and Instagram links using the buttons provided

2. **In group chats**:
   - Make sure the bot is added to the group
   - Type `/chain` to start a networking list
   - Tap "Add Me (LinkedIn)" or "Add Me (Instagram)" to add your links
   - Tap "Remove Me" to remove yourself from the chain

### For Group Admins

1. **Add the bot** to your group chat
2. **Encourage members** to set up their links privately first
3. **Start a chain** with `/chain` when ready for everyone to share
4. **Only one active chain** will be maintained - new chains automatically archive old ones

---

## 📱 Commands

- `/start` - Set up your profile and links (works in private chat)
- `/help` - Display help information
- `/chain` - Start a networking chain in a group chat
- `/edit_linkedin` - Edit your LinkedIn link
- `/edit_instagram` - Edit your Instagram link
- `/remove_linkedin` - Remove your LinkedIn link
- `/remove_instagram` - Remove your Instagram link

---

## 🌐 Deploying to Railway

1. Push this repo to your GitHub account
2. Go to [https://railway.app](https://railway.app)
3. Create a new project and select "Deploy from GitHub repo"
4. Connect and select your repository
5. Add the required environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `FIREBASE_DATABASE_URL`
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON`
6. Railway will automatically detect your Python project and deploy it
7. The service will start running immediately with the command from your Procfile or `python bot.py` by default

Railway will automatically rebuild and redeploy your bot whenever you push changes to your GitHub repository.

---

## 📄 License

[MIT](LICENSE)

---

## ✉️ Contact

Have feedback or want to collaborate? Open an issue on GitHub!