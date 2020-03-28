import logging
import os
import shutil
from tempfile import NamedTemporaryFile

import requests
import sentry_sdk
from dotenv import load_dotenv, find_dotenv
from telegram import MessageEntity, InlineQueryResultVideo, ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Updater,
    MessageHandler,
    Filters,
    InlineQueryHandler,
    CommandHandler,
)

from tiktokfetcher import TikTokFetcher

load_dotenv(find_dotenv())

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("TikBot")

updater = Updater(token=os.getenv("TELEGRAM_TOKEN"), use_context=True)
dispatcher = updater.dispatcher

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(os.getenv("SENTRY_DSN"))


def tiktok_handler(update, context):
    message = update.effective_message
    message_entities = [
        n
        for n in message.parse_entities([MessageEntity.URL]).values()
        if "vm.tiktok.com/" in n
    ]
    # The input message without the TikTok URL
    original_message = "".join(
        [str(message.text).replace(url, "") for url in message_entities]
    )
    # Iterate over all TikTok URLs
    for url in message_entities:
        process_video(update, url, original_message)


def process_video(update, url: str, text: str):
    message = update.effective_message
    if "vm.tiktok.com/" in url:
        processing_status = message.reply_markdown(
            "Downloading %s 🤯🤓😇🤖" % url, disable_notification=True
        )
        try:
            video_data = TikTokFetcher(url).get_video()
        except Exception:
            # Update the status
            processing_status.edit_text(
                "Could not download video 😭 are you sure this is a valid TikTok video?"
            )
            return
        # Initialize a temporary file in-memory for storing and then uploading the video
        with NamedTemporaryFile(suffix=".mp4") as f:
            # Get the video
            with requests.get(video_data.get("src"), stream=True) as r:
                r.raise_for_status()
                shutil.copyfileobj(r.raw, f)
            processing_status.delete()
            logger.info("Processed video %s" % url)
            video_caption = video_data.get("caption")
            caption = (
                f"*({message.from_user.name})* "
                if not text
                else f"*({message.from_user.name})* _{text}_\n "
            ) + f"\n[{video_caption}]({url})"
            reply = message.reply_video(
                open(f.name, "rb"),
                disable_notification=True,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                quote=False,
            )
            try:
                message.delete()
            except BadRequest:
                pass
            return reply


def inline_handler(update, context):
    query = update.inline_query.query.split(" ")[0]
    if query and "vm.tiktok.com" in query:
        try:
            data = TikTokFetcher(query).get_video()

            video_caption = data.get("caption")
            caption = f"\n[{video_caption}]({query})"

            results = [
                InlineQueryResultVideo(
                    id=data.get("id"),
                    video_url=data.get("src"),
                    mime_type="video/mp4",
                    caption=caption,
                    title="Send this video",
                    description=data.get("title"),
                    thumb_url="https://storage.googleapis.com/tiktokbot/icon.jpg",
                    parse_mode=ParseMode.MARKDOWN,
                )
            ]
            update.inline_query.answer(results)
        except Exception:
            return


def start(update, context):
    update.effective_message.reply_text(
        "Hey! 👋🏽 Add me to a group, send a TikTok share link and I'll reply with the actual video!"
    )


if __name__ == "__main__":
    handler = MessageHandler(
        (Filters.entity(MessageEntity.URL) | Filters.entity(MessageEntity.TEXT_LINK)),
        tiktok_handler,
    )
    dispatcher.add_handler(handler)
    dispatcher.add_handler(InlineQueryHandler(inline_handler))
    dispatcher.add_handler(CommandHandler("start", start))
    logger.info("TikBot booted")
    updater.start_polling()
    updater.idle()
