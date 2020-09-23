import json
import re

from requests_html import HTMLSession

from headers import TIKTOK_CDN_HEADERS


class TikTokError(Exception):
    pass


class TikTokFetcher:
    def __init__(self, url: str):
        """
        Initialize a new TikTok Fetcher
        :param url: TikTok share URL
        """
        link_regex = re.compile(r"^https:\/\/(www|m|vm)\.tiktok\.com\/.+$")
        assert link_regex.match(url), "Invalid TikTok share link"
        self.url = url

        # Initialize the requests session
        self.session = HTMLSession()
        self.session.headers = TIKTOK_CDN_HEADERS

    def get_video(self) -> dict:
        """
        Get the configured video's src and caption
        :return: dict
        """
        # Fetch the original URL
        req = self.session.get(self.url)
        scripts = [
            n
            for n in req.html.find("script")
            if n.text.startswith("window.__INIT_PROPS__")
            or n.attrs.get("id") == "__NEXT_DATA__"
        ]
        if scripts[0].attrs.get("id") == "__NEXT_DATA__":
            # Attempt to use alternative method of obtaining videoData
            src = json.loads(str(scripts[0].text))
            video_data = src.get("props", {}).get("pageProps", {}).get("videoData", {})
        else:
            src = json.loads(
                str(scripts[0].text).replace("window.__INIT_PROPS__ = ", "")
            )
            video_data = src.get("/v/:id", {}).get("videoData", {})
        assert len(video_data.keys()) != 0, "Returned video data is empty"
        return video_data
