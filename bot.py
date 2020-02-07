import logging
import os
import shutil
import tempfile
from tempfile import TemporaryFile, NamedTemporaryFile
from uuid import uuid4

import requests
from dotenv import load_dotenv, find_dotenv
from telegram import MessageEntity, InlineQueryResultArticle, InputTextMessageContent, ParseMode, InlineQueryResultVideo
from telegram.ext import Updater, MessageHandler, Filters, run_async, InlineQueryHandler, CommandHandler
from telegram.utils.helpers import escape_markdown

from tiktok import TikTok

load_dotenv(find_dotenv())

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("TikBot")

updater = Updater(token=os.getenv("TELEGRAM_TOKEN"), use_context=True)
dispatcher = updater.dispatcher


@run_async
def tiktok_handler(update, context):
    message = update.effective_message
    for url in message.parse_entities([MessageEntity.URL]).values():
        process_video(update, url)


@run_async
def process_video(update, url):
    message = update.effective_message
    if "https://vm.tiktok.com/" in url:
        status = message.reply_markdown(u"Downloading %s 🤯🤓😇🤖" % url, disable_notification=True)
        with NamedTemporaryFile(suffix=".mp4") as f:
            data = TikTok(url).get_video()
            with requests.get(data.get("src"), stream=True) as r:
                r.raise_for_status()
                shutil.copyfileobj(r.raw, f)
            status.delete()
            logger.info("Processed video %s" % url)
            message.reply_video(open(f.name, "rb"), disable_notification=True, caption=data.get("caption"))


@run_async
def inline_handler(update, context):
    query = update.inline_query.query
    if "https://vm.tiktok.com" in query:
        data = TikTok(query, render=True).get_video()
        results = [
            InlineQueryResultVideo(
                id=data.get("id"),
                video_url=data.get("src"),
                mime_type="video/mp4",
                caption=data.get("caption"),
                title="Send this video",
                description=data.get("title"),
                thumb_url=data.get("thumbnail")
            )]
        update.inline_query.answer(results)


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
