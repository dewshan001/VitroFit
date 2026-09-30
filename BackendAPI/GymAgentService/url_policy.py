"""URL rules shared by the tool guard and the deterministic validator (pure, no I/O).

One implementation on purpose: the host the scraper may fetch and the hosts an evidence
citation may name are judged by the same code, so the two can never drift apart.
"""

import ipaddress
import os
from urllib.parse import urlparse

MAX_URL_LENGTH = 500
ALLOWED_PORTS = (None, 80, 443)

# Reason codes returned by check_url.
TOO_LONG = "TOO_LONG"
UNPARSEABLE = "UNPARSEABLE"
BAD_SCHEME = "BAD_SCHEME"
HAS_CREDENTIALS = "HAS_CREDENTIALS"
BAD_PORT = "BAD_PORT"
IP_LITERAL = "IP_LITERAL"
INTERNAL_HOST = "INTERNAL_HOST"

DEFAULT_ALLOWLIST = "facebook.com,instagram.com,tripadvisor.com,yelp.com,maps.google.com"


def _with_scheme(url: str) -> str:
    url = (url or "").strip()
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def normalise_host(url: str) -> str:
    """Lower-cased hostname without a leading www. ('' if it cannot be parsed)."""
    try:
        host = urlparse(_with_scheme(url)).hostname or ""
    except ValueError:
        return ""
    return host.lower().rstrip(".").removeprefix("www.")


def host_is_internal(host: str) -> bool:
    """True for hosts that must never be fetched or cited (loopback, private ranges, *.local)."""
    if host in ("localhost", "") or host.endswith((".local", ".internal", ".localhost")):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast


def check_url(url: str, own_host: str | None = None) -> str | None:
    """None if the URL is acceptable as a source, else a reason code.

    https is required, except that the gym's own host may use http (many small gym sites
    still do). No credentials, no odd ports, no IP literals, no internal addresses.
    """
    if not url or len(url) > MAX_URL_LENGTH:
        return TOO_LONG
    if "://" in url and not url.strip().lower().startswith(("http://", "https://")):
        return BAD_SCHEME
    try:
        parsed = urlparse(_with_scheme(url))
        port = parsed.port
    except ValueError:
        return UNPARSEABLE
    host = normalise_host(url)
    if not host:
        return UNPARSEABLE
    if parsed.username or parsed.password or "@" in (parsed.netloc or ""):
        return HAS_CREDENTIALS
    if port not in ALLOWED_PORTS:
        return BAD_PORT
    try:
        ipaddress.ip_address(host)
        return IP_LITERAL if not host_is_internal(host) else INTERNAL_HOST
    except ValueError:
        pass
    if host_is_internal(host):
        return INTERNAL_HOST
    scheme = parsed.scheme.lower()
    if scheme != "https" and not (scheme == "http" and own_host and host == own_host):
        return BAD_SCHEME
    return None


def configured_allowlist() -> list[str]:
    """Domains (besides the gym's own site) that may be cited. Read on every call so a
    changed GYM_URL_ALLOWLIST takes effect without a restart of tests or tooling."""
    raw = os.getenv("GYM_URL_ALLOWLIST")
    raw = DEFAULT_ALLOWLIST if raw is None else raw
    return [d.strip().lower().removeprefix("www.") for d in raw.split(",") if d.strip()]


def host_matches(host: str, domain: str) -> bool:
    """Domain-boundary match: 'm.facebook.com' matches 'facebook.com'; 'evilfacebook.com'
    and 'facebook.com.evil.com' do not."""
    return host == domain or host.endswith("." + domain)


def is_allowed_host(host: str, own_host: str | None) -> bool:
    if not host:
        return False
    if own_host and host == own_host:
        return True
    return any(host_matches(host, d) for d in configured_allowlist())


def url_key(url: str) -> str:
    """Comparable form of a URL: host + path, ignoring scheme, www., query, fragment and a
    trailing slash. Two spellings of the same page compare equal."""
    try:
        parsed = urlparse(_with_scheme(url))
    except ValueError:
        return ""
    return f"{normalise_host(url)}{parsed.path.rstrip('/')}".lower()
