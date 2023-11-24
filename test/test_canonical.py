"""Test canonical components beyond Google's test suite."""

# pkg
from freshlinks.canonicalize import canonical_ip
from freshlinks.canonicalize import canonical_host
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


def test_empty_path() -> None:
    """Empty path."""
    assert canonical_path("") == "/"
    assert canonical_path("foo") == "/foo"


def test_bytes_url_fragment() -> None:
    """Bytes URL"""
    assert canonical_url(b"http://example.com#foo") == b"http://example.com"
    assert (
        canonical_url(b"http://example.com#!foo")
        == b"http://example.com?_escaped_fragment=foo"
    )
