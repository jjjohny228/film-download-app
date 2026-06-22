import asyncio
from pathlib import Path
from typing import Callable, TypeVar

from .models import Proxy, User, db

T = TypeVar("T")


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db.init(db_path)
    db.connect(reuse_if_open=True)
    db.create_tables([User, Proxy], safe=True)


async def run_sync(fn: Callable[..., T], *args: object, **kwargs: object) -> T:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))
