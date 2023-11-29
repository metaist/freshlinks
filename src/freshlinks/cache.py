"""Cache URL response."""

# native
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from time import time
from typing import Dict
from typing import Any
from typing import List
from typing import Optional
from typing import Union
import re

# lib
import ujson

StrOrPath = Union[str, Path]
"""`str` or `Path`."""

DEFAULT_PATH: StrOrPath = "~/.cache/freshlinks"
"""Default cache folder."""

RE_DURATION = re.compile(r"(\d+(?:\.\d+)?)[ ]*([dhms])")
"""Pattern for time strings."""

DURATION_UNITS = {
    "d": "days",
    "h": "hours",
    "m": "minutes",
    "s": "seconds",
}
"""Time string units."""


def to_timedelta(duration: str) -> timedelta:
    """Convert a time duration string into a `timedelta`."""
    parts = re.findall(RE_DURATION, duration.lower())
    args = {"days": 0.0, "hours": 0.0, "minutes": 0.0, "seconds": 0.0}
    for value, unit in parts:
        args[DURATION_UNITS.get(unit, "seconds")] += float(value)
    return timedelta(**args)


def age_time(age: str, start: Optional[datetime] = None) -> int:
    """Return unix time relative to a start date.

    Args:
        age (str): amount of time; a number followed by a time unit
            (s=seconds, m=minutes, h=hours, d=days). `s` is default.

        start (datetime, optional): start date from which to subtract `age`.
            If `None` uses `datetime.now()`. Defaults to `None`.

    Returns:
        int: unix time relative to `start`
    """
    return int(((start or datetime.now()) - to_timedelta(age)).timestamp())


def hash_url(url: str) -> str:
    """Return the hash for a given `url`."""
    return sha256(url.encode("utf-8")).hexdigest()


@dataclass
class LinkEntry:
    is_cached: bool = False
    """Did this entry come from a cache?"""

    version: int = 1
    """Entry format version."""

    time: int = 0
    code: int = 200
    err: str = ""
    url: str = ""
    links: List[str] = field(default_factory=list)

    @staticmethod
    def load(data: Dict[str, Any]) -> LinkEntry:
        return LinkEntry(
            is_cached=True,
            version=data["v"],
            time=data["t"],
            code=data["c"],
            err=data.get("err", ""),
            url=data["url"],
            links=data["links"],
        )

    @property
    def ok(self) -> bool:
        return self.code in [200, 301, 302]

    @property
    def json(self) -> Dict[str, Any]:
        return dict(
            v=self.version,
            t=self.time,
            c=self.code,
            err=self.err,
            url=self.url,
            links=self.links,
        )


class LinkCache:
    """A file-based cache for storing metadata about URLs."""

    path: Path
    """Cache folder."""

    max_time: int = 0
    """Cache entries older than this are considered invalid."""

    def __init__(
        self,
        store: Dict[str, LinkEntry],
        max_time: int = 0,
        path: StrOrPath = DEFAULT_PATH,
        preload: bool = False,
    ):
        self.store = store
        self.max_time = max_time if max_time > 0 else int(time())
        self.path = Path(path).expanduser()
        self.path.mkdir(exist_ok=True)  # ensure cache folder exists
        if preload:
            self.preload()

    def preload(self) -> None:
        for item in self.path.glob("*.json"):
            self.load(item.stem)

    def load(self, hashed: str) -> Optional[LinkEntry]:
        path = self.path / f"{hashed}.json"
        if not path.exists():
            return None

        data = ujson.loads(path.read_text())
        if data.get("t", 0) < self.max_time:
            return None

        entry = LinkEntry.load(data)
        self.store[entry.url] = entry
        return entry

    def __contains__(self, url: str) -> bool:
        return url in self.store or (self.path / f"{hash_url(url)}.json").exists()

    def __getitem__(self, url: str) -> Optional[LinkEntry]:
        try:
            return self.store[url]
        except KeyError:
            return self.load(hash_url(url))

    def __setitem__(self, url: str, entry: LinkEntry) -> None:
        self.store[url] = entry
        if entry:
            (self.path / f"{hash_url(url)}.json").write_text(
                ujson.dumps(
                    entry.json,
                    ensure_ascii=False,
                    escape_forward_slashes=False,
                )
            )
