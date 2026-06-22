import pytest
from bot.services.proxy import parse_proxy_line, ParsedProxy, NoProxyAvailable


def test_parse_full_proxy():
    result = parse_proxy_line("http 85.195.81.148:10772:WUkKKj:fXx0qQ")
    assert result == ParsedProxy(
        protocol="http",
        host="85.195.81.148",
        port=10772,
        login="WUkKKj",
        password="fXx0qQ",
    )


def test_parse_proxy_no_auth():
    result = parse_proxy_line("socks5 1.2.3.4:1080")
    assert result == ParsedProxy(
        protocol="socks5",
        host="1.2.3.4",
        port=1080,
        login=None,
        password=None,
    )


def test_parse_proxy_invalid_raises():
    with pytest.raises(ValueError):
        parse_proxy_line("notaproxy")


def test_no_proxy_available_is_exception():
    assert issubclass(NoProxyAvailable, Exception)


def test_parse_proxy_strips_whitespace():
    result = parse_proxy_line("  http  85.195.81.148:10772:WUkKKj:fXx0qQ  ")
    assert result.host == "85.195.81.148"
    assert result.protocol == "http"
