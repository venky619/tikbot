import logging
import os
import shutil
from tempfile import NamedTemporaryFile

import requests
from dotenv import load_dotenv, find_dotenv
from telegram import MessageEntity, InlineQueryResultVideo
from telegram.ext import Updater, MessageHandler, Filters, InlineQueryHandler, CommandHandler

from tiktok import TikTok

load_dotenv(find_dotenv())

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("TikBot")

updater = Updater(token=os.getenv("TELEGRAM_TOKEN"), use_context=True)
dispatcher = updater.dispatcher


def tiktok_handler(update, context):
    message = update.effective_message
    for url in message.parse_entities([MessageEntity.URL]).values():
        process_video(update, url)


def process_video(update, url):
    message = update.effective_message
    if "https://vm.tiktok.com/" in url:
        status = message.reply_markdown(u"Downloading %s 🤯🤓😇🤖" % url, disable_notification=True)
        try:
            data = TikTok(url).get_video()
        except Exception as e:
            status.edit_text("Could not download video 😭 are you sure this is a valid TikTok video?")
            return
        with NamedTemporaryFile(suffix=".mp4") as f:
            with requests.get(data.get("src"), stream=True) as r:
                r.raise_for_status()
                shutil.copyfileobj(r.raw, f)
            status.delete()
            logger.info("Processed video %s" % url)
            message.reply_video(open(f.name, "rb"), disable_notification=True, caption=data.get("caption"))


def inline_handler(update, context):
    query = update.inline_query.query.split(" ")[0]
    if query and "https://vm.tiktok.com" in query:
        try:
            data = TikTok(query).get_video()
            results = [
                InlineQueryResultVideo(
                    id=data.get("id"),
                    video_url=data.get("src"),
                    mime_type="video/mp4",
                    caption=data.get("caption"),
                    title="Send this video",
                    description=data.get("title"),
                    thumb_url="https://storage.googleapis.com/tiktokbot/icon.jpg",
                )]
            update.inline_query.answer(results)
        except Exception:
            return


def start(update, context):
    update.effective_message.reply_text("Hey! 👋🏽 Add me to a group, send a TikTok share link and I'll reply with the actual video!")


if __name__ == '__main__':
    handler = MessageHandler((Filters.entity(MessageEntity.URL) | Filters.entity(MessageEntity.TEXT_LINK)), tiktok_handler)
    dispatcher.add_handler(handler)
    dispatcher.add_handler(InlineQueryHandler(inline_handler))
    dispatcher.add_handler(CommandHandler("start", start))
    logger.info("TikBot booted")
    updater.start_polling()
    updater.idle()
