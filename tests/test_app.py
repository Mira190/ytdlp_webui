"""Offline test suite. No network, no real downloads.

Covers: HTTP routes, cross-site POST rejection, progress lifecycle and TTL
cleanup, format selection (evaluated against yt-dlp's real selection
engine via the benchmark harness), and logger memory bounds.
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from benchmarks.fixtures import CATALOGS  # noqa: E402
from benchmarks.run_format_bench import select, QUALITIES, FILE_FORMATS  # noqa: E402


@pytest.fixture
def client():
    main.app.config["TESTING"] = True
    return main.app.test_client()


@pytest.fixture(autouse=True)
def clean_progress():
    main.PROGRESS.clear()
    yield
    main.PROGRESS.clear()


# ---------------------------------------------------------------- routes

def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"downloadForm" in r.data


def test_download_requires_url(client):
    r = client.post("/download", data={"url": "  "})
    assert r.get_json()["status"] == "error"


def test_download_starts_job(client, monkeypatch):
    calls = {}
    monkeypatch.setattr(main, "download_video",
                        lambda *a, **k: calls.setdefault("args", a))
    r = client.post("/download", data={"url": "https://example.invalid/v"})
    body = r.get_json()
    assert body["status"] == "started" and body["job_id"]
    deadline = time.time() + 2
    while "args" not in calls and time.time() < deadline:
        time.sleep(0.01)
    assert calls["args"][1] == "https://example.invalid/v"
    assert main.PROGRESS[body["job_id"]]["status"] == "started"


def test_progress_unknown_job(client):
    assert client.get("/progress?job_id=nope").get_json()["status"] == "unknown"


# ----------------------------------------------------- cross-site POSTs

@pytest.mark.parametrize("headers,expected", [
    ({"Origin": "https://evil.example"}, 403),
    ({"Origin": "null"}, 403),
    ({"Origin": "http://127.0.0.1:5000", "Host": "evil.example"}, 403),
    ({"Origin": "http://127.0.0.1:5000"}, 200),
    ({"Origin": "http://localhost:5000"}, 200),
    ({}, 200),  # non-browser client without Origin
])
def test_cross_site_post_policy(client, headers, expected):
    r = client.post("/download", data={"url": ""}, headers=headers)
    assert r.status_code == expected


# ------------------------------------------------ progress hook + TTL

def test_progress_hook_lifecycle():
    hook = main.progress_hook_factory("job1")
    hook({"status": "downloading", "total_bytes": 200, "downloaded_bytes": 50,
          "speed": 1024, "eta": 3})
    assert main.PROGRESS["job1"]["percent"] == 25
    hook({"status": "finished"})
    assert main.PROGRESS["job1"]["percent"] == 100
    assert main.PROGRESS["job1"]["status"] == "finished"


def test_progress_hook_handles_missing_totals():
    hook = main.progress_hook_factory("job2")
    hook({"status": "downloading", "downloaded_bytes": 50})
    assert main.PROGRESS["job2"]["percent"] == 0  # no crash, no div-by-zero


def test_download_error_survives_cleanup(monkeypatch):
    """Regression: error entries written by download_video's except handler
    must carry updated_at, or cleanup treats them as infinitely old and
    sweeps the user's error message on the next download."""
    monkeypatch.setattr(
        main.yt_dlp, "YoutubeDL",
        lambda opts: (_ for _ in ()).throw(RuntimeError("boom")))
    main.download_video("jobX", "https://example.invalid/v",
                        "best", False, "", "default")
    assert main.PROGRESS["jobX"]["status"] == "error"
    main.cleanup_stale_progress()
    assert "jobX" in main.PROGRESS  # fresh error not swept


def test_cleanup_removes_only_stale_terminal_jobs():
    now = time.time()
    old = now - main.PROGRESS_TTL_SECONDS - 1
    main.PROGRESS.update({
        "stale-done": {"status": "finished", "updated_at": old},
        "stale-err": {"status": "error", "updated_at": old},
        "old-but-running": {"status": "downloading", "updated_at": old},
        "fresh-done": {"status": "finished", "updated_at": now},
    })
    main.cleanup_stale_progress()
    assert set(main.PROGRESS) == {"old-but-running", "fresh-done"}


# ------------------------------------------------------ format selection

@pytest.mark.parametrize("catalog", sorted(CATALOGS))
@pytest.mark.parametrize("file_format", FILE_FORMATS)
@pytest.mark.parametrize("quality", QUALITIES)
def test_every_ui_choice_selects_a_format(catalog, file_format, quality):
    fmt = main.get_format_option(quality, False, file_format)
    assert select(fmt, CATALOGS[catalog]) is not None


@pytest.mark.parametrize("catalog", sorted(CATALOGS))
def test_audio_only_selects_a_format(catalog):
    fmt = main.get_format_option("best", True, "default")
    assert select(fmt, CATALOGS[catalog]) is not None


def test_preferred_container_wins_when_available():
    fmt = main.get_format_option("720p", False, "mp4")
    assert select(fmt, CATALOGS["youtube_standard"]) == "136+140"
    fmt = main.get_format_option("720p", False, "webm")
    assert select(fmt, CATALOGS["youtube_standard"]) == "247+251"


def test_quality_cap_respected():
    fmt = main.get_format_option("480p", False, "default")
    chosen = select(fmt, CATALOGS["youtube_standard"])
    assert chosen == "244+251"  # 480p video, not 1080p


# --------------------------------------------------------------- logger

def test_logger_memory_is_bounded():
    log = main.SimpleLogger()
    for i in range(main.SimpleLogger.MAX_MESSAGES * 10):
        log.debug(f"line {i}")
    assert len(log.messages) == main.SimpleLogger.MAX_MESSAGES
    assert log.get_output().splitlines()[-1].endswith(
        f"line {main.SimpleLogger.MAX_MESSAGES * 10 - 1}")
