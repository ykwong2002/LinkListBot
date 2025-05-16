# 🤖 LinkListBot

A Telegram bot that simplifies networking in group chats by compiling LinkedIn and Instagram links into a single, editable chain message. Perfect for orientation camps, networking events, and professional group chats.

---

## 🔗 Features

- 📎 **Tap-to-add**: Users click a button to add their LinkedIn or Instagram links.
- 🧠 **Remembers profiles**: Users only need to set their links once in a private chat.
- 💬 **Chain message**: All profiles are compiled into a single message for easy viewing.
- 🔄 **Live updates**: Adds new users to the chain without spamming the group.
- 🌐 **Works in any Telegram group**: Just add the bot and start networking.

---

## 🚀 Quick Demo

Coming soon! (You can include a GIF or screenshot here)

---

## 🛠️ Tech Stack

- **Language**: Python  
- **Bot Framework**: [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot)  
- **Storage**: In-memory (can upgrade to Firebase/Supabase)  
- **Hosting**: Render / Railway (free tier compatible)  
- **Optional**: `.env` file support via `python-dotenv`

---

## 📦 Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/yourusername/linkup-bot.git
cd linkup-bot
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
````

---

## 🔐 Configuration

Create a `.env` file based on `.env.example` and fill in your Telegram bot token:

```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
```

You can get a token by creating a bot via [@BotFather](https://t.me/BotFather) on Telegram.

---

## ▶️ Run the Bot

```bash
python bot.py
```

The bot will start polling for updates. To run 24/7, deploy using Render or Railway.

---

## 🧪 Example Usage

1. Start the bot in **private chat** and set your social links:

   ```
   /start
   > Please send me your LinkedIn link.
   > Got it! Now send your Instagram link.
   ```

2. Add the bot to a **group chat**.

3. In the group, click:

   * 🔗 `Add Me (LinkedIn)`
   * 📸 `Add Me (Instagram)`

4. The bot creates or updates a message like:

   ```
   👥 Networking Links:
   1. Alice – [LinkedIn](https://linkedin.com/in/alice) | [Instagram](https://instagram.com/alice)
   2. Bob – [LinkedIn](https://linkedin.com/in/bob)
   ```

---

## 🌐 Deploying to Render

1. Push this repo to your GitHub account
2. Go to [https://render.com](https://render.com)
3. Create a **new Web Service**
4. Link your repo, set the **Start Command**:

   ```bash
   python bot.py
   ```
5. Add environment variables from `.env`
6. Deploy!

---

## 📄 License

[MIT](LICENSE)

---

## 🙌 Contributions Welcome

If you have ideas for improvements (like persistent storage, anonymous mode, or export features), feel free to open an issue or PR!

---

## ✉️ Contact

Created by [@yourusername](https://github.com/yourusername)
Have feedback or want to collaborate? DM me on Telegram or raise an issue!