"""Test cache functions."""

# native
from datetime import timedelta
from datetime import datetime

# pkg
from freshlinks.cache import to_timedelta
from freshlinks.cache import age_time
from freshlinks.cache import hash_url
from freshlinks.cache import LinkEntry


LOCALHOST = "http://localhost:8080/"


def test_to_timedelta() -> None:
    """Convert strings to time deltas."""
    assert to_timedelta("1d") == timedelta(days=1)
    assert to_timedelta("2h") == timedelta(hours=2)
    assert to_timedelta("30m") == timedelta(minutes=30)
    assert to_timedelta("45s") == timedelta(seconds=45)

    assert to_timedelta("1d 2h 30m 45s") == timedelta(
        days=1, hours=2, minutes=30, seconds=45
    )
    assert to_timedelta("1d2h30m45s") == timedelta(
        days=1, hours=2, minutes=30, seconds=45
    )

    assert to_timedelta("1.5h") == timedelta(hours=1.5)
    assert to_timedelta("0.5d 12m") == timedelta(days=0.5, minutes=12)

    assert to_timedelta("1x") == timedelta(0)


def test_age_time() -> None:
    """Convert relative durations to a unix timestamp."""
    assert age_time("1s") == int((datetime.now() - timedelta(seconds=1)).timestamp())


def test_hash_url() -> None:
    """Hash URLs."""
    test = LOCALHOST
    want = "387db443878e39df26fe9826db1fd40100b146f93795b07fda3bfeef709b5aca"
    have = hash_url(test)
    assert have == want


def test_load_entry() -> None:
    """Load an entry."""
    test = dict(v=1, t=2000, c=200, err="", url=LOCALHOST, links=[])
    want = LinkEntry(is_cached=True, time=2000, url=LOCALHOST)
    assert LinkEntry.load(test) == want
    assert want.json == test
