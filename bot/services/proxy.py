import random
from dataclasses import dataclass
from typing import Callable

from bot.database.db import run_sync
from bot.database.models import Proxy


class NoProxyAvailable(Exception):
    pass


@dataclass
class ParsedProxy:
    protocol: str
    host: str
    port: int
    login: str | None
    password: str | None


def parse_proxy_line(line: str) -> ParsedProxy:
    """Parse 'protocol host:port[:login:password]' format."""
    line = line.strip()
    parts = line.split(" ", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid proxy line: {line!r}")
    protocol = parts[0].strip().lower()
    addr = parts[1].strip().split(":")
    if len(addr) == 2:
        host, port_s = addr
        login = password = None
    elif len(addr) == 4:
        host, port_s, login, password = addr
    else:
        raise ValueError(f"Invalid proxy address: {parts[1]!r}")
    return ParsedProxy(
        protocol=protocol,
        host=host,
        port=int(port_s),
        login=login or None,
        password=password or None,
    )


_no_proxy_callbacks: list[Callable] = []


class ProxyService:
    @staticmethod
    def register_no_proxy_callback(cb: Callable) -> None:
        _no_proxy_callbacks.append(cb)

    @staticmethod
    async def get_next() -> Proxy:
        def _query() -> Proxy:
            active = list(Proxy.select().where(Proxy.is_active == True))  # noqa: E712
            if not active:
                raise NoProxyAvailable
            return random.choice(active)

        try:
            return await run_sync(_query)
        except NoProxyAvailable:
            for cb in _no_proxy_callbacks:
                await cb()
            raise

    @staticmethod
    async def mark_failed(proxy_id: int) -> bool:
        """Increments fail_count. Deactivates at >= 3. Returns True if deactivated."""

        def _mark() -> bool:
            p = Proxy.get_by_id(proxy_id)
            p.fail_count += 1
            if p.fail_count >= 3:
                p.is_active = False
            p.save()
            return not p.is_active

        deactivated = await run_sync(_mark)
        if deactivated:
            remaining = await run_sync(
                lambda: Proxy.select().where(Proxy.is_active == True).count()  # noqa: E712
            )
            if remaining == 0:
                for cb in _no_proxy_callbacks:
                    await cb()
        return deactivated

    @staticmethod
    async def add_proxies(lines: list[str]) -> int:
        added = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                p = parse_proxy_line(line)
            except ValueError:
                continue

            def _upsert(parsed: ParsedProxy = p) -> None:
                Proxy.get_or_create(
                    host=parsed.host,
                    port=parsed.port,
                    protocol=parsed.protocol,
                    defaults={
                        "login": parsed.login,
                        "password": parsed.password,
                        "is_active": True,
                        "fail_count": 0,
                    },
                )

            await run_sync(_upsert)
            added += 1
        return added

    @staticmethod
    async def get_stats() -> dict:
        def _q() -> dict:
            total = Proxy.select().count()
            active = Proxy.select().where(Proxy.is_active == True).count()  # noqa: E712
            return {"total": total, "active": active}

        return await run_sync(_q)
