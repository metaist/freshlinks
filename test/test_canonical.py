"""Test canonical components beyond Google's test suite."""

# pkg
from freshlinks.canonicalize import canonical_host
from freshlinks.canonicalize import canonical_ip
from freshlinks.canonicalize import canonical_path
from freshlinks.canonicalize import canonical_url


def test_ip_overflow() -> None:
    """High IP components."""
    assert canonical_ip("256.0.0.0") == "0.0.0.0"
    assert canonical_ip("300.0.0.0") == "44.0.0.0"
    assert canonical_ip("0.0.0.256") == "", "overflow of last component"


def test_empty_host() -> None:
    """Empty host name."""
    assert canonical_host("") == ""
    assert canonical_url(":8080") == "http://localhost:8080/"


def test_empty_path() -> None:
    """Empty path."""
    assert canonical_path("") == "/"
    assert canonical_path("foo") == "/foo"


def test_way_back_machine_path() -> None:
    """WayBackMachine path."""
    url = "https://web.archive.org/web/20230609101345/https://metaist.com/blog/"
    assert canonical_url(url) == url


def test_bytes_url_fragment() -> None:
    """Bytes URL"""
    assert canonical_url(b"http://example.com#foo") == "http://example.com/"
    assert (
        canonical_url(b"http://example.com#!foo")
        == "http://example.com/?_escaped_fragment_=foo"
    )
