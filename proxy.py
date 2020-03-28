import random

import requests


class Proxy:
    def __init__(self, ip, port, protocol):
        assert (
            ip is not None and port is not None and protocol is not None
        ), "Proxy is empty"
        self.protocol = protocol
        self.ip = ip
        self.port = port

    def to_proxy(self):
        return {self.protocol: f"{self.ip}:{self.port}"}

    def __repr__(self):
        self.to_proxy()

    def __str__(self):
        self.to_proxy()


class ProxyFetcher:
    def __init__(self, initial=None, force=False):
        if initial is None:
            initial = []
        self.data = initial
        self.url = "https://api.getproxylist.com/proxy?country[]=US&protocol=http"
        if len(self.data) < 2:
            self.fetch(True)

    def fetch(self, clear=True):
        if clear:
            self.data = []
        r = requests.get(self.url)
        r.raise_for_status()
        for proxy in r.json():
            self.data.append(
                Proxy(proxy.get("ip"), proxy.get("port"), proxy.get("protocol"))
            )

    def random(self):
        return random.choice(self.data)
