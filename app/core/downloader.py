import os
import threading

import httpx
from PySide6.QtCore import QThread, Signal


class DownloadWorker(QThread):
    progress = Signal(int, int)   # downloaded_bytes, total_bytes
    finished = Signal(str)        # absolute save_path
    error = Signal(str)           # error message

    def __init__(self, url: str, save_path: str) -> None:
        super().__init__()
        self._url = url
        self._save_path = save_path
        self._cancelled = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # start unpaused

    def cancel(self) -> None:
        self._cancelled = True
        self._pause_event.set()  # unblock if paused

    def pause(self) -> None:
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def run(self) -> None:
        f = None
        try:
            with httpx.Client(follow_redirects=True, timeout=30) as client:
                with client.stream("GET", self._url) as response:
                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    f = open(self._save_path, "wb")  # noqa: SIM115
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                        self._pause_event.wait()  # blocks while paused
                        if self._cancelled:
                            f.close()
                            f = None
                            try:
                                os.remove(self._save_path)
                            except OSError:
                                pass
                            return
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)
                    if f:
                        f.close()
                        f = None
            self.finished.emit(self._save_path)
        except Exception as e:
            if f:
                try:
                    f.close()
                except Exception:
                    pass
            self.error.emit(str(e))
