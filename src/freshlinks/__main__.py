#!/usr/bin/env python
"""Check to make sure your links are still fresh.

Usage: freshlinks
    [--help | --version] [--debug]
    [--config PATH]
    [--cache DIR] [--cache-age AGE] [--cache-ignore DOMAIN...] [--cache-retry]
    [<url>...] [--ignore URL...]
    [--domain DOMAIN...] [--depth NUM]
    [--show-ok] [--show-err]

Options:
  -h, --help                show this message and exit
  --version                 show version and exit
  --debug                   show debug messages

Config:
  -c PATH, --config PATH    path to configuration file

Cache:
  --cache DIR               directory to load and store cache files
                            [default: ~/.cache/freshlinks]

  --cache-age AGE           ignore cache data older than this age [default: 5d]
                            units: d=days; h=hours; m = minutes; s=sec

  --cache-ignore DOMAIN     ignore cache for these domains (always ping)
  --cache-retry             ignore cached result if it was an error

Check:
  <url>                     URL to check
  --ignore URL              URL to ignore

Scrape:
  --domain DOMAIN           domains to include in link checking
  --depth NUM               maximum recursion depth for checking links [default: 10]

Output:
  --show-ok                 show URLs that were successfully reached
  --show-err                show error messages
"""

# std
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from random import uniform
from time import sleep
from time import time
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import Set
from typing import Tuple

# lib
from attrbox import AttrDict
from attrbox import load_config
from attrbox import parse_docopt
from multiprocess import Manager  # type: ignore
from url_normalize.tools import deconstruct_url  # type: ignore
import ezq

# pkg
from .cache import age_time
from .cache import LinkCache
from .cache import LinkEntry
from .canonicalize import canonical_url
from .scraper import ping_url
from .scraper import scrape_links

__version__ = "1.0.0"
__pubdate__ = "unpublished"


@dataclass
class Args:
    help: bool = False
    version: bool = False
    debug: bool = False
    config: Optional[Path] = None
    cache: Optional[Path] = None
    cache_age: str = "5d"
    cache_ignore: Set[str] = field(default_factory=set)
    cache_retry: bool = False
    url: List[str] = field(default_factory=list)
    ignore: List[str] = field(default_factory=list)
    domain: Set[str] = field(default_factory=set)
    depth: int = 10
    show_ok: bool = False
    show_err: bool = False

    @staticmethod
    def load() -> Args:
        """Load CLI arguments and any configuration files."""
        args = parse_docopt(__doc__, version=__version__, read_config=False)
        config = AttrDict(load_config(Path(args.config))) if args.config else AttrDict()

        # NOTE: args overwrite configs
        for arg, val in args.items():
            if arg not in config:  # config doesn't have this arg
                config[arg] = val
            elif isinstance(val, list):  # merge lists
                config[arg] = list(config[arg] or []) + val
            elif isinstance(val, bool):  # merge bools
                config[arg] = config[arg] or val
            else:  # by default, arg wins
                config[arg] = val

        config.config = Path(config.config) if config.config else None
        config.cache = Path(config.cache) if config.cache else None
        config.cache_ignore = set(config.cache_ignore or [])
        config.url = [canonical_url(url) for url in config.url] if config.url else []
        config.depth = int(config.depth) if config.depth is not None else 10
        config.domain = set(
            config.domain or {deconstruct_url(url).host for url in (config.url or [])}
        )

        return Args(**config)


def inc_keys(stat: Dict[str, int], *keys: str) -> None:
    """Increment the string keys of a dict by 1."""
    for key in keys:
        stat[key] = stat.get(key, 0) + 1


def print_stats(stat: Dict[str, int]) -> None:
    """Print right-aligned sorted keys with values."""
    print("")
    n = max(len(k) for k in stat.keys())
    for k, v in sorted(stat.items()):
        print(f"{k: >{n}}:", v)


def print_entry(args: Args, entry: LinkEntry) -> None:
    """Print the result of a ping."""
    if entry.ok and not args.show_ok:
        return

    print(
        f"{'ERR' if entry.code == -1 else entry.code} "
        f"{'(cache) ' if entry.is_cached else ''}"
        f"{entry.url}"
    )
    if args.show_err:
        print(f" ==> {entry.err}")


def process_link(
    url: str,
    depth: int,
    args: Args,
    todo: List[Tuple[str, int]],
    done: Dict[str, Optional[LinkEntry]],
    stat: Dict[str, int],
    cache: LinkCache,
) -> None:
    domain = deconstruct_url(url).host
    do_scrape = domain in args.domain and depth <= args.depth

    entry = None
    if depth > 0 and domain not in args.cache_ignore and cache and url in cache:
        entry = cache[url]
        if entry:
            inc_keys(stat, "cache")

    if not entry or (args.cache_retry and not entry.ok):
        method: Literal["get", "head"] = "get" if do_scrape else "head"
        req, entry = ping_url(url, method)
        inc_keys(stat, f"ping:{method}")

        if do_scrape and req:
            entry.links = list(scrape_links(req))
            inc_keys(stat, "scrape")

        done[url] = entry
        if cache:
            cache[url] = entry

    inc_keys(stat, "total", str(entry.code), "ok" if entry.ok else "fail")
    print_entry(args, entry)

    if do_scrape and url not in args.ignore:
        for link in entry.links:
            if link not in done and link not in args.ignore:
                todo.append((link, depth + 1))


def worker_print(n: int, t: float, args: Args, msg: str) -> None:
    """Print a message from a worker."""
    if not args.debug:
        return
    print(f"{time() - t:07.1f} WORKER-{n}:", msg)


def worker_sleep(n: int, t: float, args: Args, todo: List[Tuple[str, int]]) -> None:
    """Sleep a worker, if needed."""
    if not todo:
        worker_print(n, t, args, "sleep")
        sleep(uniform(1, 4))  # wait for some more work
        worker_print(n, t, args, "awake")


def worker(
    n: int,
    args: Args,
    todo: List[Tuple[str, int]],
    done: Dict[str, Optional[LinkEntry]],
    stat: Dict[str, int],
    cache: LinkCache,
) -> None:
    """Run a worker."""
    t = time()
    worker_print(n, t, args, "beg")
    worker_sleep(n, t, args, todo)  # don't start too early
    while todo:
        url, depth = None, 0
        try:
            url, depth = todo.pop()
        except IndexError:  # todo might actually be empty
            pass

        if url and url not in done:  # new link
            done[url] = None  # prevent other workers
            process_link(url, depth, args, todo, done, stat, cache)

        worker_sleep(n, t, args, todo)  # don't end too early
    worker_print(n, t, args, "end")


def main() -> None:
    """Main entry point."""
    t = time()
    args = Args.load()
    if args.debug:
        print(args)

    with Manager() as manager:
        todo = manager.list([(url, 0) for url in args.url])
        done = manager.dict()
        stat = manager.dict()
        cache = (
            LinkCache(
                manager.dict(),
                max_time=age_time(args.cache_age),
                path=args.cache,
            )
            if args.cache
            else None
        )

        _bundle = (args, todo, done, stat, cache)
        for w in [ezq.run(worker, n, *_bundle) for n in range(ezq.NUM_CPUS)]:
            w.join()

        stat["time"] = f"{time() - t:2.1f}s"
        print_stats(stat)


if __name__ == "__main__":
    main()
