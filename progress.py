import time

def humanbytes(size: float) -> str:
    """Formats bytes into human readable format."""
    if not size:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

def time_formatter(seconds: int) -> str:
    """Formats seconds into readable duration string."""
    if not seconds or seconds < 0:
        return "0s"
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((f"{days}d, ") if days else "")
        + ((f"{hours}h, ") if hours else "")
        + ((f"{minutes}m, ") if minutes else "")
        + ((f"{seconds}s, ") if seconds else "")
    )
    return tmp[:-2] if tmp else "0s"

def make_progress_bar(percentage: float, total_blocks: int = 10) -> str:
    """Generates a stylish modern gradient-style progress bar."""
    filled = max(0, min(total_blocks, int(percentage / (100 / total_blocks))))
    return "▰" * filled + "▱" * (total_blocks - filled)

async def progress_for_pyrogram(current, total, ud_type, message, start_time):
    """
    Real-time high performance progress bar for Pyrogram video uploads.
    Updates every 3 seconds to avoid Telegram edit limits.
    """
    now = time.time()
    diff = now - start_time

    if round(diff % 3.0) == 0 or current == total:
        percentage = (current * 100 / total) if total > 0 else 0
        speed = current / diff if diff > 0 else 0
        eta = round((total - current) / speed) if speed > 0 else 0
        progress_bar = make_progress_bar(percentage)

        text = (
            f"**{ud_type}**\n\n"
            f"┌ **Progress:** `{progress_bar}` `{percentage:.1f}%`\n"
            f"├ **Speed:** `{humanbytes(speed)}/s`\n"
            f"├ **Uploaded:** `{humanbytes(current)}` / `{humanbytes(total)}`\n"
            f"└ **ETA:** `{time_formatter(eta)}`\n\n"
            f"⚡ *Powered by Dailymotion Cloud Engine*"
        )
        try:
            await message.edit_text(text)
        except Exception:
            pass
