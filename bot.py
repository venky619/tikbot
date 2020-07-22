import logging
import os
import shutil
from tempfile import NamedTemporaryFile

import requests
import sentry_sdk
from dotenv import load_dotenv, find_dotenv
from telegram import (
    MessageEntity,
    InlineQueryResultVideo,
    ParseMode,
    Update,
    ChatAction,
)
from telegram.error import BadRequest
from telegram.ext.dispatcher import run_async
from telegram.ext import (
    Updater,
    MessageHandler,
    Filters,
    InlineQueryHandler,
    CommandHandler,
)

from telegram.chat import Chat

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


@run_async
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
    # Grab the original reply_to_message id to use later
    reply_to_message_id = None
    if message.reply_to_message is not None:
        reply_to_message_id = message.reply_to_message.message_id
    if "vm.tiktok.com/" in url:
        try:
            video_data = TikTokFetcher(url).get_video()
        except Exception as ex:
            # Update the status
            message.reply_markdown(
                f"Could not download video 😭 are you sure this is a valid TikTok video? \n\n```{str(ex)}```",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        # Initialize a temporary file in-memory for storing and then uploading the video
        with NamedTemporaryFile(suffix=".mp4") as f:
            message.chat.send_action(action=ChatAction.UPLOAD_VIDEO)
            # Get the video
            item_infos = video_data.get("itemInfos", {})
            with requests.get(
                item_infos.get("video", {}).get("urls", [])[0], stream=True
            ) as r:
                if not r.ok:
                    logger.debug(f"Failed to download video {item_infos.get('')}")
                    message.reply_markdown(
                        f"Could not download video, TikTok gave a bad response: {r.status_code}"
                    )
                    return
                shutil.copyfileobj(r.raw, f)
            logger.info("Processed video %s" % url)
            video_caption = item_infos.get("text")
            if "#" in video_caption:
                video_caption = video_caption.split("#")[0]
            likes = item_infos.get("diggCount")
            comments = item_infos.get("commentCount")
            plays = item_infos.get("playCount")
            shares = item_infos.get("shareCount")

            user_part = ""
            if message.chat.type is not Chat.PRIVATE and message.from_user is not None:
                user_part = (
                    f"{message.from_user.name}: "
                    if not text
                    else f"{message.from_user.name}: {text}\n "
                )

            caption = (
                user_part
                + (
                    f"\n[{video_caption}]({url})\n"
                    if len(video_caption) > 0
                    else f"[TikTok]({url})"
                )
                + f"{int(likes):,} ❤️️ {int(comments):,} 💬 {int(plays):,} ▶️️ {int(shares):,} ✉️"
            )

            reply = message.reply_video(
                open(f.name, "rb"),
                disable_notification=True,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                quote=False,
                reply_to_message_id=reply_to_message_id,
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
            item_infos = data.get("itemInfos", {})
            likes = item_infos.get("diggCount")
            comments = item_infos.get("commentCount")
            plays = item_infos.get("playCount")
            shares = item_infos.get("shareCount")
            video_caption = item_infos.get("text")
            if "#" in video_caption:
                video_caption = video_caption.split("#")[0]
            meta = item_infos.get("video", {}).get("videoMeta", {})
            video_link = f"[{video_caption}]({query})" if video_caption else query
            caption = (
                video_link
                + f"\n{int(likes):,} ❤️️ {int(comments):,} 💬 {int(plays):,} ▶️️ {int(shares):,} ✉️"
            )
            results = [
                InlineQueryResultVideo(
                    id=item_infos.get("id"),
                    video_url=item_infos.get("video", {}).get("urls", [])[0],
                    mime_type="video/mp4",
                    width=meta.get("width"),
                    height=meta.get("height"),
                    caption=caption,
                    title="Send this video",
                    description=video_caption,
                    thumb_url=item_infos.get(
                        "covers", ["https://storage.googleapis.com/tiktokbot/icon.jpg"]
                    )[0],
                    parse_mode=ParseMode.MARKDOWN,
                )
            ]
            update.inline_query.answer(results)
        except Exception:
            return


def start(update, context):
    update.effective_message.reply_text(
        "Hey! 👋🏽 Add me to a group, send me a private message or mention me a TikTok share link and I'll reply with the actual video!"
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
