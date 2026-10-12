import os

# =====================================================================
# Telegram API Credentials (Get from https://my.telegram.org)
# =====================================================================
API_ID = 12345678
API_HASH = "your_api_hash_here"
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

# Admin IDs (List of admin user IDs)
ADMINS = [123456789]

# =====================================================================
# Database Configuration (MongoDB Atlas Connection URL)
# =====================================================================
MONGO_URI = "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"

# =====================================================================
# Dailymotion Cloudflare Worker API URL (Active Extractor Engine)
# =====================================================================
API_URL = "https://samra-dailymotion.krishnalucky193.workers.dev"

# =====================================================================
# Bot Session Name & Temporary Download Directory
# =====================================================================
SESSION_NAME = "dailymotion_bot_session"
DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
