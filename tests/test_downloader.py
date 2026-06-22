import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QCoreApplication

from app.core.downloader import DownloadWorker


@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance() or QCoreApplication([])
    return app


def test_download_worker_emits_finished(qapp, tmp_path):
    save_path = str(tmp_path / "test.mp4")
    worker = DownloadWorker("https://example.com/test.mp4", save_path)

    finished_paths = []
    errors = []
    worker.finished.connect(finished_paths.append)
    worker.error.connect(errors.append)

    chunk = b"x" * 1024
    mock_response = MagicMock()
    mock_response.headers = {"content-length": "1024"}
    mock_response.iter_bytes.return_value = iter([chunk])
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.core.downloader.httpx.Client", return_value=mock_client):
        worker.run()

    assert errors == []
    assert finished_paths == [save_path]
    assert os.path.exists(save_path)


def test_download_worker_emits_progress(qapp, tmp_path):
    save_path = str(tmp_path / "prog.mp4")
    worker = DownloadWorker("https://example.com/prog.mp4", save_path)

    progress_calls = []
    worker.progress.connect(lambda d, t: progress_calls.append((d, t)))

    chunk = b"y" * 512
    mock_response = MagicMock()
    mock_response.headers = {"content-length": "1024"}
    mock_response.iter_bytes.return_value = iter([chunk, chunk])
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.core.downloader.httpx.Client", return_value=mock_client):
        worker.run()

    assert len(progress_calls) == 2
    assert progress_calls[0] == (512, 1024)
    assert progress_calls[1] == (1024, 1024)


def test_download_worker_emits_error_on_failure(qapp, tmp_path):
    save_path = str(tmp_path / "err.mp4")
    worker = DownloadWorker("https://example.com/err.mp4", save_path)

    errors = []
    finished_paths = []
    worker.error.connect(errors.append)
    worker.finished.connect(finished_paths.append)

    with patch("app.core.downloader.httpx.Client", side_effect=Exception("Network error")):
        worker.run()

    assert finished_paths == []
    assert len(errors) == 1
    assert "Network error" in errors[0]


def test_cancel_stops_download(qapp, tmp_path):
    save_path = str(tmp_path / "cancel.mp4")
    worker = DownloadWorker("https://example.com/cancel.mp4", save_path)

    finished_paths = []
    worker.finished.connect(finished_paths.append)

    def cancelled_chunks():
        worker.cancel()
        yield b"z" * 512

    mock_response = MagicMock()
    mock_response.headers = {"content-length": "1024"}
    mock_response.iter_bytes.return_value = cancelled_chunks()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.core.downloader.httpx.Client", return_value=mock_client):
        worker.run()

    assert finished_paths == []
