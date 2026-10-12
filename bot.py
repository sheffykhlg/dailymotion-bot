import os
import re
import time
import asyncio
import logging
import aiohttp
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

import config
from progress import progress_for_pyrogram, time_formatter, humanbytes, make_progress_bar

# =====================================================================
# Logger Setup
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s"
)
logger = logging.getLogger("DailymotionBot")

# =====================================================================
# Network Time Calibration (Automatic Clock-Drift Correction)
# =====================================================================
def calibrate_system_clock():
    """
    Calibrates local client time with global network time.
    Guarantees MTProto packet synchronization and prevents Telegram FloodWait/Security mismatch.
    """
    import urllib.request
    from email.utils import parsedate_to_datetime
    try:
        req = urllib.request.Request("https://google.com", headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            date_hdr = res.headers.get("Date")
            if date_hdr:
                server_now = parsedate_to_datetime(date_hdr).timestamp()
                local_now = time.time()
                time_offset = int(server_now - local_now)
                logger.info(f"System clock drift offset: {time_offset}s. Calibrating MTProto session...")
                
                from pyrogram.session.internals.msg_id import MsgId
                def calibrated_msg_id(cls, *args, **kwargs) -> int:
                    now = int(time.time() + time_offset)
                    cls.offset = (cls.offset + 4) if now == cls.last_time else 0
                    msg_id = (now * 2 ** 32) + cls.offset
                    cls.last_time = now
                    return msg_id
                MsgId.__new__ = classmethod(calibrated_msg_id)

                import pyrogram.session.session as pyrogram_session
                old_init = pyrogram_session.Session.__init__
                def calibrated_init(self, *args, **kwargs):
                    old_init(self, *args, **kwargs)
                    self.time_offset = time_offset
                pyrogram_session.Session.__init__ = calibrated_init
    except Exception as e:
        logger.warning(f"Clock synchronization skipped: {e}")

calibrate_system_clock()

# =====================================================================
# Telegram Client Initialization (Persistent Session)
# =====================================================================
bot = Client(
    name=config.SESSION_NAME,
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    workdir="."
)

# =====================================================================
# MongoDB Database
# =====================================================================
db_client = AsyncIOMotorClient(config.MONGO_URI)
db = db_client["dailymotion_bot_db"]
users_col = db["users"]

async def register_user(user_id: int, first_name: str, username: str = None):
    try:
        await users_col.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "first_name": first_name,
                    "username": username,
                    "last_active": time.time()
                }
            },
            upsert=True
        )
    except Exception as err:
        logger.error(f"Database error: {err}")

# Supported Dailymotion URL Formats
DM_REGEX = re.compile(
    r"https?://(?:[a-zA-Z0-9-]+\.)?(?:dai\.ly|dailymotion\.com)/(?:video/|embed/video/)?([a-zA-Z0-9]+)",
    re.IGNORECASE
)

# =====================================================================
# Command Handlers
# =====================================================================
@bot.on_message(filters.command("start") & filters.private)
async def start_command_handler(client: Client, message: Message):
    user = message.from_user
    if user:
        await register_user(user.id, user.first_name, user.username)

    greeting_text = (
        f"👋 **Hello, {user.first_name if user else 'there'}!**\n\n"
        "Welcome to the **Dailymotion Video Downloader Bot** 🎬\n\n"
        "I can extract and deliver high-definition Dailymotion videos directly to your Telegram chat.\n\n"
        "✨ **Key Features:**\n"
        "• ⚡ High-speed Cloud Stream Processing\n"
        "• 🎥 HD / Full HD Quality Selection\n"
        "• 📊 Live Real-time Progress Tracking\n"
        "• 🖼 Original High-Resolution Thumbnails\n\n"
        "🔗 **Supported Link Formats:**\n"
        "• `https://dai.ly/...`\n"
        "• `https://www.dailymotion.com/video/...`\n"
        "• `https://geo.dailymotion.com/player/...`\n\n"
        "👉 **Send any Dailymotion video link to begin!**"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 API Endpoint", url=config.API_URL),
            InlineKeyboardButton("💬 Support Channel", url="https://t.me/telegram")
        ]
    ])
    await message.reply_text(greeting_text, reply_markup=buttons, disable_web_page_preview=True)

@bot.on_message(filters.command("help") & filters.private)
async def help_command_handler(client: Client, message: Message):
    help_text = (
        "📖 **How To Use This Bot:**\n\n"
        "1. Copy any video link from the Dailymotion app or website.\n"
        "2. Paste and send the link in this chat.\n"
        "3. The bot validates the stream via our **Cloudflare Edge API**.\n"
        "4. Your video will be downloaded, muxed, and delivered with original metadata.\n\n"
        "⚡ *Fast • Secure • Automated*"
    )
    await message.reply_text(help_text)

@bot.on_message(filters.command("stats") & filters.user(config.ADMINS))
async def stats_command_handler(client: Client, message: Message):
    try:
        total_users = await users_col.count_documents({})
        stats_text = (
            "📊 **Bot Administration Statistics**\n\n"
            f"👤 **Total Users:** `{total_users}`\n"
            f"🌐 **Connected API:** `{config.API_URL}`\n"
            "🟢 **Engine Status:** `Active & Running`"
        )
        await message.reply_text(stats_text)
    except Exception as e:
        await message.reply_text(f"❌ **Database Query Error:** {e}")

# =====================================================================
# Video Download & Upload Engine
# =====================================================================
def execute_video_download(dm_url: str, output_path: str, progress_hook):
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bv*[height<=720]+ba/b[height<=720]/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'progress_hooks': [progress_hook] if progress_hook else [],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(dm_url, download=True)

@bot.on_message(filters.text & filters.private)
async def video_link_handler(client: Client, message: Message):
    user = message.from_user
    if user:
        await register_user(user.id, user.first_name, user.username)

    match = DM_REGEX.search(message.text)
    if not match:
        return

    dm_url = match.group(0)
    status_msg = await message.reply_text("⚡ **Connecting to Cloudflare Edge API...**")

    # 1. API Verification Gateway
    api_endpoint = f"{config.API_URL}/api/info?url={dm_url}"
    api_data = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    await status_msg.edit_text(
                        f"⚠️ **API Gateway Unavailable**\n\n"
                        f"The extraction server returned HTTP `{resp.status}`.\n"
                        "Please verify your API status or try again later."
                    )
                    return
                api_data = await resp.json()
    except Exception as err:
        logger.error(f"API connection failed: {err}")
        await status_msg.edit_text(
            "❌ **API Connection Error**\n\n"
            "Could not communicate with the extraction API server.\n"
            f"Endpoint: `{config.API_URL}`"
        )
        return

    if not api_data or not api_data.get("success") or not api_data.get("master_m3u8"):
        error_msg = api_data.get("error") if api_data else "No streaming manifest found."
        await status_msg.edit_text(f"❌ **Extraction Error:** {error_msg}")
        return

    title = api_data.get("title", "Dailymotion Video")
    duration = int(api_data.get("duration", 0))
    poster_url = api_data.get("poster")

    timestamp = int(time.time())
    output_template = f"{config.DOWNLOAD_DIR}/video_{timestamp}.%(ext)s"
    thumb_path = f"{config.DOWNLOAD_DIR}/thumb_{timestamp}.jpg"

    # 2. Live Download Progress Tracker
    loop = asyncio.get_event_loop()
    last_update_tracker = [0]

    async def safe_status_update(content: str):
        try:
            await status_msg.edit_text(content)
        except Exception:
            pass

    def download_progress_callback(d):
        if d['status'] == 'downloading':
            now = time.time()
            if now - last_update_tracker[0] >= 3.0:
                last_update_tracker[0] = now
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                speed = d.get('speed') or 0
                eta = d.get('eta') or 0
                
                percentage = (downloaded * 100 / total) if total > 0 else 0
                bar = make_progress_bar(percentage)

                text = (
                    "📥 **Downloading Media Stream...**\n\n"
                    f"┌ **Progress:** `{bar}` `{percentage:.1f}%`\n"
                    f"├ **Speed:** `{humanbytes(speed)}/s`\n"
                    f"├ **Downloaded:** `{humanbytes(downloaded)}` / `{humanbytes(total)}`\n"
                    f"└ **ETA:** `{time_formatter(eta)}`\n\n"
                    f"🎬 **Title:** `{title[:45]}...`"
                )
                try:
                    asyncio.run_coroutine_threadsafe(safe_status_update(text), loop)
                except Exception:
                    pass

    try:
        await status_msg.edit_text("📥 **Stream Token Verified! Initializing download...**")
        info = await loop.run_in_executor(None, execute_video_download, dm_url, output_template, download_progress_callback)
    except Exception as err:
        logger.error(f"Download execution failure: {err}")
        await status_msg.edit_text(f"❌ **Download Failed:** {str(err)[:180]}")
        return

    # Locate downloaded file
    downloaded_file = None
    for ext in ["mp4", "mkv", "webm"]:
        candidate = f"{config.DOWNLOAD_DIR}/video_{timestamp}.{ext}"
        if os.path.exists(candidate):
            downloaded_file = candidate
            break

    if not downloaded_file:
        await status_msg.edit_text("❌ **Error:** Media processing failed. File not found.")
        return

    # 3. Thumbnail Downloader
    has_thumb = False
    if poster_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(poster_url) as t_resp:
                    if t_resp.status == 200:
                        with open(thumb_path, "wb") as f:
                            f.write(await t_resp.read())
                        has_thumb = True
        except Exception:
            has_thumb = False

    # 4. Telegram Upload with Progress
    await status_msg.edit_text("📤 **Preparing upload to Telegram cloud...**")
    upload_start_time = time.time()

    caption = (
        f"🎬 **{title}**\n\n"
        f"⏱ **Duration:** `{time_formatter(duration)}`\n"
        f"🔗 **Source:** [Dailymotion Link]({dm_url})\n\n"
        "⚡ *Processed via Dailymotion Cloud Engine*"
    )

    try:
        await message.reply_video(
            video=downloaded_file,
            caption=caption,
            duration=duration,
            thumb=thumb_path if has_thumb and os.path.exists(thumb_path) else None,
            supports_streaming=True,
            progress=progress_for_pyrogram,
            progress_args=("📤 **Uploading to Telegram...**", status_msg, upload_start_time)
        )
        await status_msg.delete()
    except Exception as upload_err:
        logger.error(f"Upload error: {upload_err}")
        await status_msg.edit_text(f"❌ **Upload Failed:** {str(upload_err)[:180]}")
    finally:
        # Storage Cleanup
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception:
                pass
        if has_thumb and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception:
                pass

if __name__ == "__main__":
    logger.info("Initializing Dailymotion Telegram Downloader Engine...")
    bot.run()
