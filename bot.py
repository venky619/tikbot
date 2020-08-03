import logging
import os
import shutil
from tempfile import NamedTemporaryFile

import requests
import sentry_sdk
from dotenv import load_dotenv, find_dotenv
from sentry_sdk import add_breadcrumb, capture_exception, configure_scope
from telegram import (
    MessageEntity,
    InlineQueryResultVideo,
    ParseMode,
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
    with configure_scope() as scope:
        message = update.effective_message
        scope.set_user(
            {"username": message.from_user.username, "id": message.from_user.link,}
        )
        scope.set_extra("message", message.text)
        message_entities = [
            n
            for n in message.parse_entities([MessageEntity.URL]).values()
            if "vm.tiktok.com/" in n or "tiktok.com/" in n
        ]
        # The input message without the TikTok URL
        original_message = "".join(
            [str(message.text).replace(url, "") for url in message_entities]
        )
        # Iterate over all TikTok URLs
        for url in message_entities:
            try:
                process_video(update, url, original_message)
            except Exception as e:
                capture_exception(e)
                logger.warning("Failed to download video %s: %s" % (url, repr(e)))
                message.reply_html(
                    "Could not process video, sorry! <pre>%s</pre>" % repr(e)
                )


def process_video(update, url: str, text: str):
    message = update.effective_message
    if "vm.tiktok.com/" in url or "tiktok.com" in url:
        add_breadcrumb(
            category="telegram",
            message="Processing video %s, requested by %s"
            % (url, message.from_user.name),
            level="info",
        )
        video_data = TikTokFetcher(url).get_video()
        # Initialize a temporary file in-memory for storing and then uploading the video
        size = -1
        with NamedTemporaryFile(suffix=".mp4") as f:
            message.chat.send_action(action=ChatAction.UPLOAD_VIDEO)
            # Get the video
            item_infos = video_data.get("itemInfos", {})
            with requests.get(
                item_infos.get("video", {}).get("urls", [])[0], stream=True
            ) as r:
                if not r.ok:
                    logger.debug(f"Failed to download video {item_infos.get('')}")
                    add_breadcrumb(
                        category="tiktok",
                        message="Failed to download video from TikTok: %s"
                        % r.status_code,
                        level="error",
                    )
                    message.reply_html(
                        f"Could not download video \U0001f613, TikTok gave a bad response \U0001f97a ({r.status_code})"
                    )
                    return
                size = int(r.headers.get("Content-Length", -2))
                shutil.copyfileobj(r.raw, f)
            logger.info("Processed video %s" % url)
            video_caption = item_infos.get("text")
            if "#" in video_caption:
                video_caption = video_caption.split("#")[0]
            likes = item_infos.get("diggCount")
            comments = item_infos.get("commentCount")
            plays = item_infos.get("playCount")
            shares = item_infos.get("shareCount")
            video_caption = video_caption.strip()

            user_part = ""
            if message.chat.type is not Chat.PRIVATE and message.from_user is not None:
                user_part = (
                    f"{message.from_user.name} "
                    if not text
                    else f"{message.from_user.name}: {text}\n "
                )

            caption = (
                user_part
                + (
                    f'\n<a href="{url}">{video_caption}</a>\n'
                    if len(video_caption.replace(" ", "")) > 0
                    else f'\n<a href="{url}">TikTok</a>\n'
                )
                + (
                    f"{int(likes):,} \u2764\ufe0f {int(comments):,} \U0001f4ad {int(plays):,} \u23ef {int(shares):,} \U0001f4ea"
                )
            )
            size = (size / 1024) / 1024
            if size > 50.0:
                add_breadcrumb(
                    category="tiktok",
                    message="Video was too large: %s" % url,
                    level="error",
                )
                caption += (
                    '\n\U0001f913\u26a1\ufe0f This video was too large to be sent via Telegram (%dmb/50mb), but you may download it <a href="%s">directly from TikTok</a>'
                ) % (size, item_infos.get("video", {}).get("urls", [])[0])
                reply = message.reply_html(caption, parse_mode=ParseMode.HTML,)
            else:
                reply = message.reply_video(
                    open(f.name, "rb"),
                    disable_notification=True,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )

            try:
                message.delete()
            except BadRequest:
                pass
            return reply


def inline_handler(update, context):
    query = update.inline_query.query.split(" ")[0]
    if query and "vm.tiktok.com" in query or "tiktok.com" in query:
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
            video_link = (
                f'\n<a href="{query}">{video_caption}</a>\n'
                if len(video_caption.replace(" ", "")) > 0
                else f'\n<a href="{query}">TikTok</a>\n'
            )
            caption = (
                video_link
                + f"{int(likes):,} \u2764\ufe0f {int(comments):,} \U0001f4ad {int(plays):,} \u23ef {int(shares):,} \U0001f4ea"
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
                    parse_mode=ParseMode.HTML,
                )
            ]
            update.inline_query.answer(results)
        except Exception:
            return


def start(update, context):
    update.effective_message.reply_text(
        "Hey! \U0001f44b\U0001f3fd Add me to a group, send me a private message or mention me a TikTok share link and I'll reply with the actual video!"
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
