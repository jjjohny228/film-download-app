import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from bot.services.proxy import NoProxyAvailable, ProxyService

_executor = ThreadPoolExecutor(max_workers=2)


@dataclass
class SearchResult:
    name: str
    url: str
    year: str
    type_: str
    poster: str


@dataclass
class FilmInfo:
    name: str
    poster: str
    is_series: bool
    translators: dict[str, str] = field(default_factory=dict)  # {name: id_str}
    seasons: dict[int, list[int]] = field(default_factory=dict)  # {season: [episodes]}


def _proxy_dict(proxy_url: str) -> dict:
    return {"http": proxy_url, "https": proxy_url}


def _sync_search(query: str, rezka_url: str, proxy_url: str) -> list[SearchResult]:
    from HdRezkaApi import HdRezkaSearch

    proxy = _proxy_dict(proxy_url)
    searcher = HdRezkaSearch(rezka_url, proxy=proxy)
    results_obj = searcher(query, find_all=True)
    items = results_obj.get_page(1) or []  # first page only, fast
    output = []
    for item in items:
        output.append(
            SearchResult(
                name=str(item.get("title", "")),
                url=str(item.get("url", "")),
                year="",
                type_=type(item.get("category", "")).__name__,
                poster=str(item.get("image", "")),
            )
        )
    return output


def _sync_get_film_info(url: str, proxy_url: str) -> FilmInfo:
    from HdRezkaApi import HdRezkaApi, TVSeries

    proxy = _proxy_dict(proxy_url)
    film = HdRezkaApi(url, proxy=proxy)

    tr_raw = film.translators  # {id: {"name": ..., "premium": ...}}
    translators = {v["name"]: str(k) for k, v in tr_raw.items()}

    is_series = film.type == TVSeries
    seasons: dict[int, list[int]] = {}

    if is_series:
        try:
            series_info = film.seriesInfo
            if series_info:
                first_tr_data = next(iter(series_info.values()))
                eps_dict = first_tr_data.get("episodes", {})
                for season_num in first_tr_data.get("seasons", {}).keys():
                    seasons[int(season_num)] = list(eps_dict.get(season_num, {}).keys())
        except Exception:
            pass

    poster = ""
    try:
        poster = film.thumbnailHQ
    except Exception:
        try:
            poster = film.thumbnail
        except Exception:
            pass

    return FilmInfo(
        name=film.name,
        poster=poster,
        is_series=is_series,
        translators=translators,
        seasons=seasons,
    )


def _sync_get_stream_url(
    url: str,
    translation: str,
    quality: str,
    season: int,
    episode: int,
    proxy_url: str,
) -> str:
    from HdRezkaApi import HdRezkaApi

    proxy = _proxy_dict(proxy_url)
    film = HdRezkaApi(url, proxy=proxy)

    if season and episode:
        stream = film.getStream(season=season, episode=episode, translation=translation)
    else:
        stream = film.getStream(translation=translation)

    urls = stream(quality)  # returns list[str]
    if not urls:
        raise ValueError(f"No URLs for quality {quality!r}")
    return urls[0]


class RezkaService:
    def __init__(self, rezka_url: str) -> None:
        self.rezka_url = rezka_url

    async def _run(self, fn, *args, max_retries: int = 3):
        loop = asyncio.get_event_loop()
        last_err: Exception | None = None

        for _ in range(max_retries):
            try:
                proxy = await ProxyService.get_next()
                proxy_url = proxy.to_url()
            except NoProxyAvailable:
                raise

            try:
                result = await loop.run_in_executor(
                    _executor,
                    lambda pu=proxy_url: fn(*args, pu),
                )
                return result
            except Exception as e:
                msg = str(e)
                if "403" in msg or "503" in msg:
                    await ProxyService.mark_failed(proxy.id)
                    last_err = e
                else:
                    raise

        raise last_err  # type: ignore[misc]

    async def search(self, query: str) -> list[SearchResult]:
        return await self._run(_sync_search, query, self.rezka_url)

    async def get_film_info(self, url: str) -> FilmInfo:
        return await self._run(_sync_get_film_info, url)

    async def get_stream_url(
        self,
        url: str,
        translation: str,
        quality: str,
        season: int = 0,
        episode: int = 0,
    ) -> str:
        return await self._run(_sync_get_stream_url, url, translation, quality, season, episode)
