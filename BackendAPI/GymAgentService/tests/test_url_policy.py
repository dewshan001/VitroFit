import pytest

import url_policy as up
from url_policy import (
    check_url,
    configured_allowlist,
    host_is_internal,
    is_allowed_host,
    normalise_host,
    url_key,
)

OWN = "fitzone.lk"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://fitzone.lk", None),
        ("https://www.fitzone.lk/about?x=1#top", None),
        ("http://fitzone.lk/classes", None),                     # http allowed on the gym's own host only
        ("HTTPS://FitZone.LK", None),
        ("https://facebook.com/fitzone", None),
        ("http://facebook.com/fitzone", up.BAD_SCHEME),           # http elsewhere is refused
        ("ftp://fitzone.lk", up.BAD_SCHEME),
        ("javascript://fitzone.lk/%0Aalert(1)", up.BAD_SCHEME),
        ("file:///etc/passwd", up.BAD_SCHEME),
        ("https://user:pw@fitzone.lk", up.HAS_CREDENTIALS),
        ("https://fitzone.lk@evil.com", up.HAS_CREDENTIALS),      # the classic host-confusion trick
        ("https://fitzone.lk:8443/x", up.BAD_PORT),
        ("https://fitzone.lk:443/x", None),
        ("https://93.184.216.34/x", up.IP_LITERAL),
        ("https://127.0.0.1", up.INTERNAL_HOST),
        ("https://10.0.0.5", up.INTERNAL_HOST),
        ("https://169.254.169.254/latest", up.INTERNAL_HOST),
        ("https://[::1]/", up.INTERNAL_HOST),
        ("https://localhost", up.INTERNAL_HOST),
        ("https://printer.local", up.INTERNAL_HOST),
        ("https://db.internal", up.INTERNAL_HOST),
        ("", up.TOO_LONG),
        ("https://fitzone.lk/" + "a" * 500, up.TOO_LONG),
    ],
)
def test_check_url(url, expected):
    assert check_url(url, OWN) == expected


def test_http_on_own_host_needs_own_host_to_be_known():
    assert check_url("http://fitzone.lk", None) == up.BAD_SCHEME


@pytest.mark.parametrize(
    "host,expected",
    [
        ("fitzone.lk", True),                     # own host
        ("facebook.com", True),
        ("m.facebook.com", True),                 # subdomain of an allowed domain
        ("maps.google.com", True),
        ("evilfacebook.com", False),              # must match on a domain boundary
        ("facebook.com.evil.com", False),
        ("notfitzone.lk", False),
        ("google.com", False),                    # only maps.google.com is listed
        ("random-blog.example", False),
        ("", False),
    ],
)
def test_allowed_hosts(host, expected):
    assert is_allowed_host(host, OWN) is expected


def test_without_a_known_own_host_only_the_configured_list_applies():
    assert is_allowed_host("fitzone.lk", None) is False
    assert is_allowed_host("facebook.com", None) is True


def test_allowlist_is_configurable_and_read_at_call_time(monkeypatch):
    monkeypatch.setenv("GYM_URL_ALLOWLIST", " Example.org , www.gymdb.io ,")
    assert configured_allowlist() == ["example.org", "gymdb.io"]
    assert is_allowed_host("sub.example.org", None) and is_allowed_host("gymdb.io", None)
    assert not is_allowed_host("facebook.com", None)


def test_empty_allowlist_means_only_the_gyms_own_site(monkeypatch):
    monkeypatch.setenv("GYM_URL_ALLOWLIST", "")
    assert configured_allowlist() == []
    assert is_allowed_host("fitzone.lk", OWN) and not is_allowed_host("facebook.com", OWN)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.FitZone.lk/", "fitzone.lk"),
        ("http://fitzone.lk", "fitzone.lk"),
        ("fitzone.lk", "fitzone.lk"),
        ("https://fitzone.lk.", "fitzone.lk"),
        ("https://fitzone.lk:443/x", "fitzone.lk"),
        ("", ""),
    ],
)
def test_normalise_host(url, expected):
    assert normalise_host(url) == expected


def test_url_key_treats_spellings_of_one_page_as_equal():
    same = ["https://fitzone.lk", "http://www.fitzone.lk/", "https://FitZone.lk/?utm=1#x"]
    assert len({url_key(u) for u in same}) == 1
    assert url_key("https://fitzone.lk/about") != url_key("https://fitzone.lk/")
    assert url_key("https://fitzone.lk/about/") == url_key("https://fitzone.lk/about")
    assert url_key("https://other.lk/about") != url_key("https://fitzone.lk/about")


@pytest.mark.parametrize("host", ["localhost", "a.local", "b.internal", "127.0.0.1", "192.168.1.1", "224.0.0.1", ""])
def test_internal_hosts(host):
    assert host_is_internal(host)


@pytest.mark.parametrize("host", ["fitzone.lk", "8.8.8.8", "facebook.com"])
def test_public_hosts_are_not_internal(host):
    assert not host_is_internal(host)
