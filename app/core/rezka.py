from dataclasses import dataclass, field

from HdRezkaApi import HdRezkaApi, HdRezkaSearch, TVSeries

DEFAULT_URL = "https://hdrezka.ag"


@dataclass
class SearchResult:
    title: str
    url: str
    year: str
    is_series: bool
    poster: str = ""


@dataclass
class FilmInfo:
    name: str
    is_series: bool
    translators: dict[str, str] = field(default_factory=dict)  # {name: id_str}
    seasons: dict[int, list[int]] = field(default_factory=dict)  # {season: [episodes]}


def search(query: str, base_url: str = DEFAULT_URL) -> list[SearchResult]:
    searcher = HdRezkaSearch(base_url)
    results_obj = searcher(query, find_all=True)
    items = results_obj.get_page(1) or []
    output = []
    for item in items:
        category = item.get("category", "")
        is_series = "сериал" in str(category).lower() or "аниме" in str(category).lower()
        output.append(
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                year=str(item.get("year", "")),
                is_series=is_series,
                poster=str(item.get("image", "")),
            )
        )
    return output


def get_film_info(url: str) -> FilmInfo:
    film = HdRezkaApi(url)
    translators = {v["name"]: str(k) for k, v in film.translators.items()}
    is_series = film.type == TVSeries
    seasons: dict[int, list[int]] = {}

    if is_series:
        try:
            series_info = film.seriesInfo
            if series_info:
                first_tr_data = next(iter(series_info.values()))
                eps_dict = first_tr_data.get("episodes", {})
                for season_str in first_tr_data.get("seasons", {}).keys():
                    s = int(season_str)
                    seasons[s] = [int(e) for e in eps_dict.get(season_str, {}).keys()]
        except Exception:
            pass

    return FilmInfo(
        name=film.name,
        is_series=is_series,
        translators=translators,
        seasons=seasons,
    )


def get_stream_url(
    url: str,
    translator_id: str,
    quality: str,
    season: int = 0,
    episode: int = 0,
) -> str:
    film = HdRezkaApi(url)
    if season > 0 and episode > 0:
        stream = film.getStream(season=season, episode=episode, translation=translator_id)
    else:
        stream = film.getStream(translation=translator_id)
    urls = stream(quality)
    if not urls:
        raise ValueError(f"No stream URLs for quality {quality!r}")
    return urls[0]
