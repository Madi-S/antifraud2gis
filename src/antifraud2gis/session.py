import requests
from .settings import settings

session = requests.Session()

if session.proxies is None and settings.proxy is not None:
    session.proxies = {
        "http": settings.proxy,
        "https": settings.proxy
    }

session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
})

