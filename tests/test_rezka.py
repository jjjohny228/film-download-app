from unittest.mock import MagicMock, patch

from app.core.rezka import (
    DEFAULT_URL,
    FilmInfo,
    SearchResult,
    get_film_info,
    get_stream_url,
    search,
)


def _make_search_item(title="Inception", url="https://hdrezka.ag/films/1/"):
    item = MagicMock()
    item.__getitem__ = lambda self, k: {
        "title": title,
        "url": url,
        "year": "2010",
        "category": "Фильмы",
    }[k]
    item.get = lambda k, d=None: {
        "title": title,
        "url": url,
        "year": "2010",
        "category": "Фильмы",
    }.get(k, d)
    return item


def test_search_returns_list():
    mock_page = [_make_search_item()]
    mock_results = MagicMock()
    mock_results.get_page.return_value = mock_page

    mock_searcher_instance = MagicMock(return_value=mock_results)

    with patch("app.core.rezka.HdRezkaSearch", return_value=mock_searcher_instance):
        results = search("Inception", base_url=DEFAULT_URL)

    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].title == "Inception"


def test_search_empty_returns_empty_list():
    mock_results = MagicMock()
    mock_results.get_page.return_value = []
    mock_searcher_instance = MagicMock(return_value=mock_results)

    with patch("app.core.rezka.HdRezkaSearch", return_value=mock_searcher_instance):
        results = search("xyzxyz_not_found", base_url=DEFAULT_URL)

    assert results == []


def test_get_film_info_movie():
    from HdRezkaApi import Film

    mock_film = MagicMock()
    mock_film.name = "Inception"
    mock_film.type = Film
    mock_film.translators = {1: {"name": "Дублированный", "premium": False}}
    mock_film.thumbnail = "https://example.com/poster.jpg"

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        info = get_film_info("https://hdrezka.ag/films/1/")

    assert isinstance(info, FilmInfo)
    assert info.name == "Inception"
    assert info.is_series is False
    assert "Дублированный" in info.translators
    assert info.seasons == {}


def test_get_film_info_series():
    from HdRezkaApi import TVSeries

    mock_film = MagicMock()
    mock_film.name = "Breaking Bad"
    mock_film.type = TVSeries
    mock_film.translators = {1: {"name": "Дублированный", "premium": False}}
    mock_film.thumbnail = "https://example.com/poster.jpg"
    mock_film.seriesInfo = {
        "1": {
            "seasons": {"1": "Season 1", "2": "Season 2"},
            "episodes": {
                "1": {"1": "E1", "2": "E2"},
                "2": {"1": "E1"},
            },
        }
    }

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        info = get_film_info("https://hdrezka.ag/series/1/")

    assert info.is_series is True
    assert 1 in info.seasons
    assert info.seasons[1] == [1, 2]
    assert info.seasons[2] == [1]


def test_get_stream_url_movie():
    mock_stream = MagicMock()
    mock_stream.return_value = ["https://cdn.example.com/video.mp4"]

    mock_film = MagicMock()
    mock_film.getStream.return_value = mock_stream

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        url = get_stream_url(
            "https://hdrezka.ag/films/1/",
            translator_id="1",
            quality="1080p",
            season=0,
            episode=0,
        )

    assert url == "https://cdn.example.com/video.mp4"
    mock_film.getStream.assert_called_once_with(translation="1")


def test_get_stream_url_series_episode():
    mock_stream = MagicMock()
    mock_stream.return_value = ["https://cdn.example.com/s01e01.mp4"]

    mock_film = MagicMock()
    mock_film.getStream.return_value = mock_stream

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        url = get_stream_url(
            "https://hdrezka.ag/series/1/",
            translator_id="1",
            quality="720p",
            season=1,
            episode=1,
        )

    assert url == "https://cdn.example.com/s01e01.mp4"
    mock_film.getStream.assert_called_once_with(season=1, episode=1, translation="1")


def test_get_stream_url_raises_on_empty():
    mock_stream = MagicMock(return_value=[])
    mock_film = MagicMock()
    mock_film.getStream.return_value = mock_stream

    import pytest

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        with pytest.raises(ValueError, match="No stream URLs"):
            get_stream_url("https://hdrezka.ag/films/1/", "1", "1080p", 0, 0)
