from tempfile import TemporaryFile

import requests
from requests_html import AsyncHTMLSession, HTMLSession


class TikTok:
    def __init__(self, url: str):
        assert "https://vm.tiktok.com" in url, "Invalid TikTok share link"
        self.url = url
        self.session = HTMLSession()

        self.session.headers = {
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7,fr;q=0.6',
            'user-agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/44.0.2403.155 Safari/537.36',
            'accept': '*/*',
            'dnt': '1',
        }

    def get_video_url(self) -> str:
        req = self.session.get(self.url)
        assert req.ok, "Could not make request to tiktok: %s" % req
        src = req.html.find("video", first=True).attrs.get("src")
        assert src is not None, "Could not find video"
        return src

    def get_video(self) -> bytes:
        src = self.get_video_url()
        return requests.get(src).content
