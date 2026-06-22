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

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            with httpx.Client(follow_redirects=True, timeout=30) as client:
                with client.stream("GET", self._url) as response:
                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    with open(self._save_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                            if self._cancelled:
                                return
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.progress.emit(downloaded, total)
            self.finished.emit(self._save_path)
        except Exception as e:
            self.error.emit(str(e))
