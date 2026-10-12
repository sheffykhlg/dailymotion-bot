# 🎬 Dailymotion Video Downloader Bot (Telegram)

An enterprise-grade, high-performance **Dailymotion Video Downloader Telegram Bot** powered by **Pyrogram**, **yt-dlp**, and **Cloudflare Worker Edge API**.

---

## 🌟 Key Features

- ⚡ **Cloudflare Edge Gateway Integration**: Validates stream manifest, tokens, and formats dynamically via your private API.
- ⏱ **Automated Network Time Synchronization**: Automatically patches Windows / Server clock drift to prevent MTProto `msg_id` desync and FloodWait penalties.
- 📊 **Dual Real-time Animated Progress Bars**: Live updates for both Stream Download and Telegram Cloud Upload phases (`Speed`, `Size`, `ETA`, `Progress Bar`).
- 🖼 **High-Res Thumbnail & Metadata Preservation**: Embeds custom video thumbnails, titles, and formatted video duration.
- 💾 **Persistent Session Support**: Uses `.session` file to eliminate repeated auth sessions across container restarts.
- 🗄 **MongoDB Integration**: Asynchronous user registration and administration analytics via `motor`.
- 🐳 **Dockerized Deployment**: Production-ready `Dockerfile` with multi-platform dependencies pre-configured.

---

## 📁 Repository Structure

```text
├── bot.py             # Main Pyrogram Bot core & event handlers
├── config.py          # Direct configuration file (Fill your credentials here)
├── progress.py        # Modern stylized dual progress bar generator
├── requirements.txt   # Python dependency list
├── Dockerfile         # Automated Docker container build
└── README.md          # Project documentation
```

---

## 🚀 Getting Started

### 1. Clone & Configure

```bash
git clone https://github.com/sheffykhlg/dailymotion-bot.git
cd dailymotion-bot
```

Open `config.py` and replace the dummy placeholders with your credentials:

```python
API_ID = 12345678
API_HASH = "your_api_hash_here"
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
ADMINS = [123456789]
MONGO_URI = "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"
```

*(Note: `API_URL` is already configured with your active Cloudflare Worker).*

### 2. Local Installation & Launch

```bash
pip install -r requirements.txt
python bot.py
```

---

## 🐳 Docker Deployment

Run seamlessly on any cloud provider (Render, Koyeb, Railway, VPS):

```bash
docker build -t dailymotion-bot .
docker run -d --name dailymotion-bot-instance dailymotion-bot
```

---

## 🔒 Security & Privacy

- Strictly connects to your designated **Dailymotion Extractor API**.
- Temporary files and thumbnails are purged immediately post-upload to conserve disk space.
- Production `.session` files are ignored in version control via `.gitignore`.
