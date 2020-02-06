# TikBot

This bot will post the video of a TikTok share link as a Telegram Video to avoid the unreliable Telegram web preview.

## Configuration

The only configuration variable needed is `TELEGRAM_TOKEN`.

You can either set it while deploying the docker image with `docker run` or with an `.env` file (using `docker-compose`).