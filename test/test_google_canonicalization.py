"""Test `canonical_ip` and `canonical_url` using Google's test suite.

See:
    - https://developers.google.com/safe-browsing/v4/urls-hashing#canonicalization
    - https://chromium.googlesource.com/external/google-safe-browsing/+/06a8c4e799233da220ad7411e2bfacc74cbfbb37/python/expression_test.py
"""

# This file is a partial rewrite of Google's Python 2.5 implementation.
#
# Copyright 2023 Metaist LLC.
# Licensed under the MIT License.
#
# The original `expression_test.py` file carries this license:
#
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pkg
from freshlinks.canonicalize import canonical_ip
from freshlinks.canonicalize import canonical_url


def test_canonicalize_ip() -> None:
    """Canonicalize IP addresses."""
    items = [
        ("1.2.3.4", "1.2.3.4"),
        ("012.034.01.055", "10.28.1.45"),
        ("0x12.0x43.0x44.0x01", "18.67.68.1"),
        ("167838211", "10.1.2.3"),
        ("12.0x12.01234", "12.18.2.156"),
        ("0x10000000b", "0.0.0.11"),
        ("asdf.com", ""),
        ("0x120x34", ""),
        ("123.123.0.0.1", ""),
        ("1.2.3.00x0", ""),
        ("fake ip", ""),
        ("123.123.0.0.1", ""),
        ("255.0.0.1", "255.0.0.1"),
        ("12.0x12.01234", "12.18.2.156"),
        # TODO: Make this test case work.
        # This doesn't seem very logical to me, but it might be how microsoft's
        # dns works.  Certainly it's how Netcraft does it.
        # ('276.2.3', '20.2.0.3'),
        ("012.034.01.055", "10.28.1.45"),
        ("0x12.0x43.0x44.0x01", "18.67.68.1"),
        ("167838211", "10.1.2.3"),
        ("3279880203", "195.127.0.11"),
        ("4294967295", "255.255.255.255"),
        ("10.192.95.89 xy", "10.192.95.89"),
        ("1.2.3.00x0", ""),
        # If we find bad octal parse the whole IP as decimal or hex.
        ("012.0xA0.01.089", "12.160.1.89"),
    ]
    for test, want in items:
        have = canonical_ip(test)
        assert have == want, f"test input: {test}, actual:{have}, expected: {want}"


def test_canonicalize_url() -> None:
    """Canonicalize URLs."""
    items = [
        ("http://google.com/", "http://google.com/"),
        ("http://google.com:80/a/b", "http://google.com/a/b"),
        ("http://google.com:80/a/b/c/", "http://google.com/a/b/c/"),
        ("http://GOOgle.com", "http://google.com/"),
        ("http://..google..com../", "http://google.com/"),
        ("http://google.com/%25%34%31%25%31%46", "http://google.com/A%1F"),
        ("http://google^.com/", "http://google^.com/"),
        ("http://google.com/1/../2/././", "http://google.com/2/"),
        ("http://google.com/1//2?3//4", "http://google.com/1/2?3//4"),
        # Some more examples of our url lib unittest.
        ("http://host.com/%25%32%35", "http://host.com/%25"),
        ("http://host.com/%25%32%35%25%32%35", "http://host.com/%25%25"),
        ("http://host.com/%2525252525252525", "http://host.com/%25"),
        ("http://host.com/asdf%25%32%35asd", "http://host.com/asdf%25asd"),
        ("http://host.com/%%%25%32%35asd%%", "http://host.com/%25%25%25asd%25%25"),
        ("http://www.google.com/", "http://www.google.com/"),
        (
            "http://%31%36%38%2e%31%38%38%2e%39%39%2e%32%36/%2E%73%65%63%75%72%65/%77%77%77%2E%65%62%61%79%2E%63%6F%6D/",
            "http://168.188.99.26/.secure/www.ebay.com/",
        ),
        (
            "http://195.127.0.11/uploads/%20%20%20%20/.verify/.eBaysecure=updateuserdataxplimnbqmn-xplmvalidateinfoswqpcmlx=hgplmcx/",
            "http://195.127.0.11/uploads/%20%20%20%20/.verify/.eBaysecure=updateuserdataxplimnbqmn-xplmvalidateinfoswqpcmlx=hgplmcx/",
        ),
        (
            "http://host%23.com/%257Ea%2521b%2540c%2523d%2524e%25f%255E00%252611%252A22%252833%252944_55%252B",
            "http://host%23.com/~a!b@c%23d$e%25f^00&11*22(33)44_55+",
        ),
        ("http://3279880203/blah", "http://195.127.0.11/blah"),
        ("http://www.google.com/blah/..", "http://www.google.com/"),
        ("http://a.com/../b", "http://a.com/b"),
        ("www.google.com/", "http://www.google.com/"),
        ("www.google.com", "http://www.google.com/"),
        ("http://www.evil.com/blah#frag", "http://www.evil.com/blah"),
        ("http://www.GOOgle.com/", "http://www.google.com/"),
        ("http://www.google.com.../", "http://www.google.com/"),
        ("http://www.google.com/foo\tbar\rbaz\n2", "http://www.google.com/foobarbaz2"),
        ("http://www.google.com/q?", "http://www.google.com/q?"),
        ("http://www.google.com/q?r?", "http://www.google.com/q?r?"),
        ("http://www.google.com/q?r?s", "http://www.google.com/q?r?s"),
        ("http://evil.com/foo#bar#baz", "http://evil.com/foo"),
        ("http://evil.com/foo;", "http://evil.com/foo;"),
        ("http://evil.com/foo?bar;", "http://evil.com/foo?bar;"),
        (b"http://\x01\x80.com/", "http://%01%80.com/"),
        ("http://notrailingslash.com", "http://notrailingslash.com/"),
        ("http://www.gotaport.com:1234/", "http://www.gotaport.com:1234/"),
        ("http://www.google.com:443/", "http://www.google.com:443/"),
        ("  http://www.google.com/  ", "http://www.google.com/"),
        ("http:// leadingspace.com/", "http://%20leadingspace.com/"),
        ("http://%20leadingspace.com/", "http://%20leadingspace.com/"),
        ("%20leadingspace.com/", "http://%20leadingspace.com/"),
        ("https://www.securesite.com:443/", "https://www.securesite.com/"),
        ("ftp://ftp.myfiles.com:21/", "ftp://ftp.myfiles.com/"),
        # ("http://some%1Bhost.com/%1B", "http://some%1Bhost.com/%1B"),
        # NOTE: Unlike Google, we ensure that the host name is always lower-cased.
        ("http://some%1Bhost.com/%1B", "http://some%1bhost.com/%1B"),
        # Test NULL character
        (b"http://test%00\x00.com/", "http://test%00%00.com/"),
        # Username and password should be removed
        # ("http://user:password@google.com/", "http://google.com/"),
        # NOTE: Unlike Google, we keep the username and password.
        ("http://user:password@google.com/", "http://user:password@google.com/"),
        # All of these cases are missing a valid hostname and should return ''
        ("", ""),
        (":", ""),
        ("/blah", ""),
        ("#ref", ""),
        ("/blah#ref", ""),
        ("?query#ref", ""),
        ("/blah?query#ref", ""),
        ("/blah;param", ""),
        ("http://#ref", ""),
        ("http:///blah#ref", ""),
        ("http://?query#ref", ""),
        ("http:///blah?query#ref", ""),
        ("http:///blah;param", ""),
        ("http:///blah;param?query#ref", ""),
        ("mailto:bryner@google.com", ""),
        # If the protocol is unrecognized, the URL class does not parse out
        # a hostname.
        # ("myprotocol://site.com/", ""),
        # This URL should _not_ have hostname shortening applied to it.
        (
            "http://i.have.way.too.many.dots.com/",
            "http://i.have.way.too.many.dots.com/",
        ),
        # WholeSecurity escapes parts of the scheme
        ("http%3A%2F%2Fwackyurl.com:80/", "http://wackyurl.com/"),
        ("http://W!eird<>Ho$^.com/", "http://w!eird<>ho$^.com/"),
        # The path should have a leading '/' even if the hostname was terminated
        # by something other than a '/'.
        ("ftp://host.com?q", "ftp://host.com/?q"),
    ]
    for test, want in items:
        have = canonical_url(test)
        assert have == want, f"test input: {test}, actual: {have}, expected: {want}"


def test_url_() -> None:
    """Run Google's Canonicalization tests.

    See: https://developers.google.com/safe-browsing/v4/urls-hashing#canonicalization
    """
    Canonicalize = canonical_url
    assert Canonicalize("http://host/%25%32%35") == "http://host/%25"
    assert Canonicalize("http://host/%25%32%35%25%32%35") == "http://host/%25%25"
    assert Canonicalize("http://host/%2525252525252525") == "http://host/%25"
    assert Canonicalize("http://host/asdf%25%32%35asd") == "http://host/asdf%25asd"
    assert (
        Canonicalize("http://host/%%%25%32%35asd%%") == "http://host/%25%25%25asd%25%25"
    )
    assert Canonicalize("http://www.google.com/") == "http://www.google.com/"
    assert (
        Canonicalize(
            "http://%31%36%38%2e%31%38%38%2e%39%39%2e%32%36/%2E%73%65%63%75%72%65/%77%77%77%2E%65%62%61%79%2E%63%6F%6D/"
        )
        == "http://168.188.99.26/.secure/www.ebay.com/"
    )
    assert (
        Canonicalize(
            "http://195.127.0.11/uploads/%20%20%20%20/.verify/.eBaysecure=updateuserdataxplimnbqmn-xplmvalidateinfoswqpcmlx=hgplmcx/"
        )
        == "http://195.127.0.11/uploads/%20%20%20%20/.verify/.eBaysecure=updateuserdataxplimnbqmn-xplmvalidateinfoswqpcmlx=hgplmcx/"
    )
    assert (
        Canonicalize(
            "http://host%23.com/%257Ea%2521b%2540c%2523d%2524e%25f%255E00%252611%252A22%252833%252944_55%252B"
        )
        == "http://host%23.com/~a!b@c%23d$e%25f^00&11*22(33)44_55+"
    )
    assert Canonicalize("http://3279880203/blah") == "http://195.127.0.11/blah"
    assert Canonicalize("http://www.google.com/blah/..") == "http://www.google.com/"
    assert Canonicalize("www.google.com/") == "http://www.google.com/"
    assert Canonicalize("www.google.com") == "http://www.google.com/"
    assert Canonicalize("http://www.evil.com/blah#frag") == "http://www.evil.com/blah"
    assert Canonicalize("http://www.GOOgle.com/") == "http://www.google.com/"
    assert Canonicalize("http://www.google.com.../") == "http://www.google.com/"
    assert (
        Canonicalize("http://www.google.com/foo\tbar\rbaz\n2")
        == "http://www.google.com/foobarbaz2"
    )
    assert Canonicalize("http://www.google.com/q?") == "http://www.google.com/q?"
    assert Canonicalize("http://www.google.com/q?r?") == "http://www.google.com/q?r?"
    assert Canonicalize("http://www.google.com/q?r?s") == "http://www.google.com/q?r?s"
    assert Canonicalize("http://evil.com/foo#bar#baz") == "http://evil.com/foo"
    assert Canonicalize("http://evil.com/foo;") == "http://evil.com/foo;"
    assert Canonicalize("http://evil.com/foo?bar;") == "http://evil.com/foo?bar;"
    assert Canonicalize(b"http://\x01\x80.com/") == "http://%01%80.com/"
    assert Canonicalize("http://notrailingslash.com") == "http://notrailingslash.com/"
    # NOTE: Unlike Google, we do not remove non-default ports.
    # assert Canonicalize("http://www.gotaport.com:1234/") == "http://www.gotaport.com/"
    assert Canonicalize("  http://www.google.com/  ") == "http://www.google.com/"
    assert Canonicalize("http:// leadingspace.com/") == "http://%20leadingspace.com/"
    assert Canonicalize("http://%20leadingspace.com/") == "http://%20leadingspace.com/"
    assert Canonicalize("%20leadingspace.com/") == "http://%20leadingspace.com/"
    assert Canonicalize("https://www.securesite.com/") == "https://www.securesite.com/"
    assert Canonicalize("http://host.com/ab%23cd") == "http://host.com/ab%23cd"
    assert (
        Canonicalize("http://host.com//twoslashes?more//slashes")
        == "http://host.com/twoslashes?more//slashes"
    )
