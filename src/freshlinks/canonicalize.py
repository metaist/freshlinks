"""Generate canonical URLs roughly using Google's Safe Browsing standard.

Differences:
- Fragments are removed, but `#!` is converted to `?_escaped_fragment_=`
- Username and password are NOT removed from the host.

See:
- https://developers.google.com/safe-browsing/v4/urls-hashing#canonicalization
- https://chromium.googlesource.com/external/google-safe-browsing/+/06a8c4e799233da220ad7411e2bfacc74cbfbb37/python/expression.py
- https://github.com/niksite/url-normalize/blob/master/url_normalize/url_normalize.py
"""

# This file is a rewrite of Google's Python 2.5 implementation.
#
# Copyright 2023 Metaist LLC.
# Licensed under the MIT License.
#
# The original `expression.py` file carries this license:
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

# native
from typing import List
from typing import Union
from urllib.parse import quote
from urllib.parse import unquote
from urllib.parse import unquote_to_bytes
import re
import string

# lib
from attrbox import AttrDict
from url_normalize.tools import deconstruct_url
from url_normalize.tools import reconstruct_url
from url_normalize.url_normalize import normalize_port
from url_normalize.url_normalize import normalize_query
from url_normalize.url_normalize import normalize_userinfo
from url_normalize.url_normalize import provide_url_scheme

DEFAULT_SCHEME = "http"
"""Default scheme that browsers uses."""

SAFE_CHARS = "".join(
    c
    for c in string.digits + string.ascii_letters + string.punctuation
    if c not in "%#"
)
"""Characters that are not escaped."""

IP_WITH_TRAILING_SPACE = re.compile(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) ")
POSSIBLE_IP = re.compile(r"^((?:0x[0-9a-f]+|[0-9\\.])+)$", flags=re.I)
FIND_BAD_OCTAL_REGEXP = re.compile(r"(^|\.)0\d*[89]")

HEX = re.compile(r"^0x([a-fA-F0-9]+)$")
OCT = re.compile(r"^0([0-7]+)$")
DEC = re.compile(r"^(\d+)$")


def unquote2(string: Union[str, bytes]) -> Union[str, bytes]:
    """Unquote both strings and bytes."""
    if isinstance(string, bytes):
        return unquote_to_bytes(string)
    return unquote(string)


def escape(string: Union[str, bytes]) -> str:
    """Fully escape `string`, then re-escape once.

    See: https://chromium.googlesource.com/external/google-safe-browsing/+/06a8c4e799233da220ad7411e2bfacc74cbfbb37/python/expression.py#292
    """
    unquoted = unquote2(string)
    while unquoted != string:
        string = unquoted
        unquoted = unquote2(unquoted)
    return quote(unquoted, SAFE_CHARS)


def canonical_ip(host: str) -> str:
    """Return a canonical IP address."""
    if len(host) <= 15:
        # This handles the Windows resolver allows an IP
        # followed by a space and something else as long as it
        # is under 15 characters.
        if m := IP_WITH_TRAILING_SPACE.match(host):
            host = m.group(1)

    if not POSSIBLE_IP.match(host):
        return ""

    # Try to parse octal, if possible.
    allow_octal = not FIND_BAD_OCTAL_REGEXP.search(host)

    # Skip trailing, leading and consecutive dots.
    parts = [part for part in host.split(".") if part]
    if len(parts) > 4:
        return ""

    ip: List[str] = []
    for i, part in enumerate(parts):
        if m := HEX.match(part):
            base = 16
        elif allow_octal and (m := OCT.match(part)):
            base = 8
        elif m := DEC.match(part):
            base = 10
        else:
            return ""

        # print("part:", part, "m:", m.group(1), "base:", base)
        n = int(m.group(1), base)
        if n <= 255:
            ip.append(str(n))
            continue

        # print("n > 255:", n)
        if i < len(parts) - 1:
            n &= 0xFF
            ip.append(str(n))
        else:
            bar = bytearray()
            while n > 0 and len(bar) < 4:
                bar.append(n & 0xFF)
                n >>= 8

            if len(ip) + len(bar) > 4:
                return ""

            bar.reverse()
            ip.extend(str(b) for b in bar)

    return ".".join((ip + (["0"] * 4))[:4])


def canonical_host(host: str) -> str:
    """Return a canonical hostname."""
    # 0: IDN host names should be converted to ASCII punycode
    # 1: Remove all leading and trailing dots.
    # 2: Replace consecutive dots with a single dot.
    # 3: If the hostname can be parsed as an IP address, normalize it to
    #    4 dot-separated decimal values. The client should handle any legal IP-address
    #    encoding, including octal, hex, and fewer than four components.
    # 4: Lowercase the whole string.

    # See: https://chromium.googlesource.com/external/google-safe-browsing/+/06a8c4e799233da220ad7411e2bfacc74cbfbb37/python/expression.py#207
    if not host:
        return ""

    result = host.lower()  # Rule 4
    result = ".".join([part for part in result.split(".") if part])  # Rule 1 & 2
    result = result.encode("idna").decode("utf-8")  # Rule 0

    if ip := canonical_ip(host):  # Rule 3
        return ip

    return result


def canonical_path(path: str) -> str:
    """Return a canonical path."""
    # 1: Resolve the sequences "/../" and "/./" in the path by replacing "/./" with "/",
    #    and removing "/../" along with the preceding path component.
    # 2: Replace runs of consecutive slashes with a single slash character.

    # See: https://chromium.googlesource.com/external/google-safe-browsing/+/06a8c4e799233da220ad7411e2bfacc74cbfbb37/python/expression.py#157
    result = path
    if not result:
        return "/"

    if result[0] != "/":
        result = f"/{result}"

    result = escape(result)
    parts: List[str] = []
    for part in result.split("/"):
        if part == "..":  # remove previous part (if any)
            if len(parts) > 0:
                parts.pop()
        elif part and part != ".":  # skip empty and .
            parts.append(part)

    result = f"/{'/'.join(parts)}"
    if path.endswith("/") and not result.endswith("/"):
        result = f"{result}/"
    # leading and trailing slashes added (if needed)

    return result


def canonical_url(url: Union[str, bytes]) -> str:
    """Return a canonical version of `url`.

    See: https://developers.google.com/safe-browsing/v4/urls-hashing#canonicalization
    See: https://chromium.googlesource.com/external/google-safe-browsing/+/06a8c4e799233da220ad7411e2bfacc74cbfbb37/python/expression.py
    """
    # 4: Remove tab (0x09), CR (0x0d), and LF (0x0a) characters from the URL.
    #    Do not remove escape sequences for these characters (e.g. '%0a').

    # 1: URL is valid RFC 2396
    # 2: Convert internationalized domain name (IDN) to ASCII Punycode.
    # 3: URL must include a path.
    # 5: Remove the fragment.
    # 6: Repeatedly percent-unescape the URL until it has no more percent-escapes.
    url = url.strip()  # no leading or trailing whitespace

    if isinstance(url, bytes):
        url = url.replace(b"\t", b"").replace(b"\r", b"").replace(b"\n", b"")  # Rule 4
        url = url.replace(b"#!", b"?_escaped_fragment_=")  # Different than Google
        if (pos := url.find(b"#")) >= 0:
            url = url[0:pos]  # Rule 5
    else:
        url = url.replace("\t", "").replace("\r", "").replace("\n", "")  # Rule 4
        url = url.replace("#!", "?_escaped_fragment_=")  # Different than Google
        if (pos := url.find("#")) >= 0:
            url = url[0:pos]  # Rule 5

    url = escape(url)  # in case, e.g., scheme has encoded characters
    url = provide_url_scheme(url, DEFAULT_SCHEME)

    parts = AttrDict(deconstruct_url(url)._asdict())
    if not parts.host:
        return ""

    parts.scheme = parts.scheme.lower()
    parts.userinfo = normalize_userinfo(parts.userinfo)
    parts.host = canonical_host(parts.host)
    parts.port = normalize_port(parts.port, parts.scheme)
    parts.path = canonical_path(parts.path)
    parts.query = normalize_query(parts.query)
    parts.fragment = ""

    result = reconstruct_url(parts)
    if url.endswith("?") and not result.endswith("?"):
        result += "?"

    return result
