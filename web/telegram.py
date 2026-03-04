"""Telegram notification sender for job completion/failure."""

import logging

from config import BASE_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def send_notification(message: str) -> bool:
    """Send a plain-text Telegram message. Returns False on any failure."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        from telegram import Bot
        import asyncio

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))
        return True
    except Exception:
        logger.exception("Failed to send Telegram notification")
        return False


def notify_job_completed(video_title: str, video_id: str) -> None:
    """Send a success notification with a link to the summary."""
    message = (
        f"\u2705 Summary ready!\n\n"
        f"{video_title}\n"
        f"{BASE_URL}/s/{video_id}/"
    )
    send_notification(message)


def notify_job_failed(youtube_url: str, error: str) -> None:
    """Send a failure notification with the URL and error."""
    message = (
        f"\u274c Job failed\n\n"
        f"{youtube_url}\n"
        f"Error: {error}"
    )
    send_notification(message)
