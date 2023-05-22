#!/usr/bin/env python
"""Check web links to make sure they're still available."""

# native
from time import sleep
import re

# lib
from bs4 import BeautifulSoup
from multiprocess import Manager
import ezq
import requests

BASE_URL = "http://localhost:8080"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
}

RE_CSS_IMPORT = re.compile(r"""@import ["']([^"']+)""", re.MULTILINE)
RE_CSS_URL = re.compile(r"url\s*\(\s*([^)]+)\s*\)", re.MULTILINE)


def is_alive(link, done):
    ok, req = True, None
    try:
        req = requests.get(link, timeout=3, headers=HEADERS)
        done[link] = dict(code=req.status_code)
        print(f"{req.status_code} {link}")
        if req.status_code != 200:
            ok = False
    except Exception as e:
        ok = False
        done[link] = dict(code="ERR")
        print(f"ERR {link}", e)
    return ok, req


def get_css_links(req):
    text = req.text
    for pattern in [RE_CSS_IMPORT, RE_CSS_URL]:
        for link in pattern.findall(text):
            yield link


def get_xhtml_links(soup):
    for tag in soup.select("[src],[href]"):
        if "src" in tag.attrs:
            yield tag["src"]
        elif "href" in tag.attrs:
            yield tag["href"]


def add_links(req):
    ctype = req.headers["Content-Type"]
    if ctype.startswith("text/css") or req.url.endswith(".css"):
        links = get_css_links(req)
    elif ctype.startswith("text/xml") or req.url.endswith(".xml"):
        links = get_xhtml_links(BeautifulSoup(req.content, features="xml"))
    else:
        links = get_xhtml_links(BeautifulSoup(req.content, features="html.parser"))

    for link in links:
        if (
            link.startswith("#")  # fragment
            or link.startswith("mailto:")  # email
            or link.startswith("data:")  # base64-encoded data
        ):
            continue

        if link.startswith("/"):
            link = f"{BASE_URL}{link}"

        # TODO: add relative links

        if link:
            yield link


def worker(todo: list, done: dict):
    while todo:
        if not todo:
            sleep(3)
            continue

        link = todo.pop()
        if link not in done:  # new link
            done[link] = None  # prevent other workers
            ok, req = is_alive(link, done)
            if ok and link.startswith(BASE_URL):  # scrape this link
                for item in add_links(req):
                    if item not in done:  # only add new links
                        todo.append(item)

        if not todo:  # maybe we're all done
            sleep(3)


def main():
    with Manager() as manager:
        todo, done = manager.list(), manager.dict()

        _, req = is_alive(f"{BASE_URL}/blog", done)
        for link in add_links(req):
            todo.append(link)

        for w in [ezq.run(worker, todo, done) for _ in range(ezq.NUM_CPUS)]:
            w.join()


if __name__ == "__main__":
    main()
