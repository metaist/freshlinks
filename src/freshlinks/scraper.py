"""Ping and scrape links."""

# std
from time import time
from typing import Iterator
from typing import Literal
from typing import Optional
from typing import Tuple
from urllib.parse import urljoin
import re

# lib
import requests
from requests import Response
from bs4 import BeautifulSoup

# pkg
from .cache import LinkEntry
from .canonicalize import canonical_url

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    )
}
"""HTTP headers to send when pinging."""

CSS_IMPORT = re.compile(r"""@import ["']([^"']+)""", re.MULTILINE)
"""Match a CSS `@import` expression."""

CSS_URL = re.compile(r"url\s*\(\s*([^)]+)\s*\)", re.MULTILINE)
"""Match a CSS `url()` expression."""

LINK_ATTRS = ["href", "src"]
"""HTML attributes that contain a URL."""

LINK_SELECT = ",".join(f"[{a}]" for a in LINK_ATTRS)
"""Query for selecting HTML tags that have URLs."""

LINK_IGNORE = re.compile(r"^(#|data:|mailto:|tel:)")
"""Pattern of links to ignore."""


def ping_url(
    url: str, method: Literal["head", "get"] = "get"
) -> Tuple[Optional[Response], LinkEntry]:
    """Make a request and return the response (if any) and `LinkEntry`."""
    t = int(time())
    try:
        res = getattr(requests, method)(url, timeout=3, headers=HEADERS)
        return res, LinkEntry(time=t, code=res.status_code, url=url)
    except Exception as e:
        return None, LinkEntry(time=t, code=-1, err=str(e), url=url)


def css_links(text: str) -> Iterator[str]:
    """Yield the links in a CSS document."""
    for pattern in [CSS_IMPORT, CSS_URL]:
        for link in pattern.findall(text):
            yield link


def html_links(soup: BeautifulSoup) -> Iterator[str]:
    """Yield the links in an HTML document."""
    for tag in soup.select(LINK_SELECT):
        if tag.name == "link" and "preconnect" in tag.get_attribute_list("rel", []):
            continue  # skip non-URL connection hints

        for attr in LINK_ATTRS:
            if attr in tag.attrs:
                yield tag.get_attribute_list(attr, [""])[0]


def scrape_links(res: Response) -> Iterator[str]:
    """Yield links in a `Response` based on content-type."""
    base = res.url
    ctype = res.headers["Content-Type"]
    links: Iterator[str] = iter([])

    if not ctype.startswith("text/"):  # skip non-textual (images, zip files)
        pass
    elif ctype.startswith("text/css") or base.endswith(".css"):
        links = css_links(res.text)
    elif ctype.startswith("text/xml") or base.endswith(".xml"):
        links = html_links(BeautifulSoup(res.content, features="xml"))
    else:  # assume HTML
        soup = BeautifulSoup(res.content, features="html.parser")
        links = html_links(soup)
        for tag in soup.find_all("base"):
            if "href" in tag.attrs:
                base = tag["href"]
                break  # only the first href counts

    for link in links:
        if not LINK_IGNORE.match(link):
            yield canonical_url(urljoin(base, link))
