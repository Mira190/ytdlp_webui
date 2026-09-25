"""Tests for main.py. No network or ffmpeg needed: yt_dlp.YoutubeDL is faked."""

import os
import threading
import time

import pytest
import yt_dlp

import main

WAIT_TIMEOUT = 5


class FakeYoutubeDL:
    """Stand-in for yt_dlp.YoutubeDL; download() runs the test's behaviour."""

    instances = []
    behaviour = None

    def __init__(self, opts):
        self.opts = opts
        FakeYoutubeDL.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def download(self, urls):
        if FakeYoutubeDL.behaviour is not None:
            FakeYoutubeDL.behaviour(self, urls)

    def progress(self, d):
        for hook in self.opts["progress_hooks"]:
            hook(d)

    def postprocess(self, d):
        for hook in self.opts["postprocessor_hooks"]:
            hook(d)


@pytest.fixture(autouse=True)
def clean_progress():
    with main.PROGRESS_LOCK:
        main.PROGRESS.clear()
    yield
    with main.PROGRESS_LOCK:
        main.PROGRESS.clear()


@pytest.fixture
def client():
    main.app.config["TESTING"] = True
    return main.app.test_client()


@pytest.fixture
def fake_ydl(monkeypatch):
    FakeYoutubeDL.instances = []
    FakeYoutubeDL.behaviour = None
    monkeypatch.setattr(main.yt_dlp, "YoutubeDL", FakeYoutubeDL)
    yield FakeYoutubeDL
    FakeYoutubeDL.behaviour = None


def only_job():
    """Snapshot of the single job in PROGRESS (tests run one job at a time)."""
    with main.PROGRESS_LOCK:
        (job_id,) = main.PROGRESS
    return main.get_progress_snapshot(job_id)


def wait_for_job(job_id):
    """Join the job's download thread, then return its final progress entry."""
    for thread in threading.enumerate():
        if thread.name == f"download-{job_id[:8]}":
            thread.join(timeout=WAIT_TIMEOUT)
            assert not thread.is_alive(), "download thread did not finish in time"
    return main.get_progress_snapshot(job_id)


def start(client, tmp_path, **overrides):
    data = {"url": "https://example.com/watch?v=abc", "download_dir": str(tmp_path)}
    data.update(overrides)
    return client.post("/download", data=data)


# --- build_format_options ---------------------------------------------------


def test_build_format_options_audio_only():
    opts = main.build_format_options("720p", True, "mp4")
    assert opts["format"] == "bestaudio/best"
    assert opts["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
    ]
    assert "merge_output_format" not in opts


@pytest.mark.parametrize(
    ("file_format", "quality", "expected_format", "expected_merge"),
    [
        (
            "mp4",
            "best",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
            "mp4",
        ),
        (
            "mp4",
            "720p",
            "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]"
            "/bestvideo[height<=720]+bestaudio/best[height<=720]",
            "mp4",
        ),
        (
            "webm",
            "best",
            "bestvideo[ext=webm]+bestaudio[ext=webm]/bestvideo+bestaudio/best",
            "webm",
        ),
        (
            "webm",
            "720p",
            "bestvideo[ext=webm][height<=720]+bestaudio[ext=webm]"
            "/bestvideo[height<=720]+bestaudio/best[height<=720]",
            "webm",
        ),
        ("mkv", "best", "bestvideo+bestaudio/best", "mkv"),
        ("mkv", "720p", "bestvideo[height<=720]+bestaudio/best[height<=720]", "mkv"),
        ("default", "best", "bestvideo+bestaudio/best", None),
        ("default", "720p", "bestvideo[height<=720]+bestaudio/best[height<=720]", None),
    ],
)
def test_build_format_options_video(file_format, quality, expected_format, expected_merge):
    opts = main.build_format_options(quality, False, file_format, ffmpeg_available=True)
    assert opts["format"] == expected_format
    assert opts.get("merge_output_format") == expected_merge
    assert "postprocessors" not in opts


@pytest.mark.parametrize(
    ("file_format", "quality", "expected_format"),
    [
        ("mp4", "best", "best[ext=mp4]/best"),
        ("mp4", "720p", "best[ext=mp4][height<=720]/best[height<=720]"),
        ("webm", "best", "best[ext=webm]/best"),
        ("mkv", "480p", "best[height<=480]"),
        ("default", "best", "best"),
        ("default", "1080p", "best[height<=1080]"),
    ],
)
def test_build_format_options_video_without_ffmpeg(file_format, quality, expected_format):
    """Without ffmpeg only single-file formats are requested; nothing to merge."""
    opts = main.build_format_options(quality, False, file_format, ffmpeg_available=False)
    assert opts == {"format": expected_format}


def test_build_format_options_defaults_to_detected_ffmpeg(monkeypatch):
    monkeypatch.setattr(main, "FFMPEG_AVAILABLE", False)
    assert main.build_format_options("best", False, "default") == {"format": "best"}
    monkeypatch.setattr(main, "FFMPEG_AVAILABLE", True)
    assert main.build_format_options("best", False, "default") == {
        "format": "bestvideo+bestaudio/best"
    }


# --- /download validation ---------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"url": ""},
        {"url": "   "},
        {"url": "ftp://example.com/video"},
        {"url": "example.com/video"},
        {"quality": "9999p"},
        {"file_format": "avi"},
    ],
)
def test_start_download_rejects_invalid_input(client, tmp_path, fake_ydl, overrides):
    response = start(client, tmp_path, **overrides)
    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    assert response.get_json()["output"]
    assert main.PROGRESS == {}
    assert fake_ydl.instances == []


def test_start_download_starts_job_and_finishes(client, tmp_path, fake_ydl):
    release = threading.Event()
    fake_ydl.behaviour = lambda ydl, urls: release.wait(WAIT_TIMEOUT)

    response = start(client, tmp_path)

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "started"
    job_id = body["job_id"]
    assert main.PROGRESS[job_id]["status"] == "started"

    release.set()
    final = wait_for_job(job_id)
    assert final["status"] == "finished"
    assert final["percent"] == 100
    assert "updated_at" in final

    (ydl,) = fake_ydl.instances
    assert ydl.opts["noplaylist"] is True
    assert ydl.opts["outtmpl"] == os.path.join(str(tmp_path), "%(title)s.%(ext)s")


# --- job lifecycle ----------------------------------------------------------


def test_hook_sequence_reports_processing_until_download_returns(client, tmp_path, fake_ydl):
    seen = []

    def behaviour(ydl, urls):
        ydl.progress(
            {
                "status": "downloading",
                "filename": os.path.join(str(tmp_path), "video.f137.mp4"),
                "downloaded_bytes": 50,
                "total_bytes": 200,
                "speed": 10.0,
                "eta": 15,
            }
        )
        seen.append(only_job())
        ydl.progress({"status": "finished", "filename": "video.f137.mp4"})
        seen.append(only_job())
        ydl.postprocess({"status": "started", "postprocessor": "Merger"})
        seen.append(only_job())
        ydl.postprocess({"status": "finished", "postprocessor": "Merger"})
        seen.append(only_job())

    fake_ydl.behaviour = behaviour
    job_id = start(client, tmp_path).get_json()["job_id"]
    final = wait_for_job(job_id)

    downloading, hook_finished, pp_started, pp_finished = seen
    assert downloading["status"] == "downloading"
    assert downloading["percent"] == 25
    assert downloading["downloaded_bytes"] == 50
    assert downloading["total_bytes"] == 200
    assert downloading["filename"] == "video.f137.mp4"

    assert hook_finished["status"] == "processing"
    assert hook_finished["percent"] == 100
    assert hook_finished["filename"] == "video.f137.mp4"  # merged, not replaced

    assert pp_started["status"] == "processing"
    assert pp_started["postprocessor"] == "Merger"
    assert pp_finished["status"] == "processing"

    assert final["status"] == "finished"
    assert final["percent"] == 100
    assert final["eta"] == 0


def test_download_error_is_recorded_with_timestamp(client, tmp_path, fake_ydl):
    def behaviour(ydl, urls):
        raise yt_dlp.utils.DownloadError("ERROR: boom")

    fake_ydl.behaviour = behaviour
    before = time.time()
    job_id = start(client, tmp_path).get_json()["job_id"]
    final = wait_for_job(job_id)

    assert final["status"] == "error"
    assert "boom" in final["error"]
    assert final["updated_at"] >= before


# --- /progress --------------------------------------------------------------


def test_progress_unknown_job_returns_404(client):
    response = client.get("/progress?job_id=does-not-exist")
    assert response.status_code == 404
    assert response.get_json() == {"status": "unknown"}


def test_progress_returns_known_job(client):
    main.set_progress("job-1", status="started", percent=0)
    response = client.get("/progress?job_id=job-1")
    assert response.status_code == 200
    assert response.get_json()["status"] == "started"


# --- cleanup_stale_progress -------------------------------------------------


def test_cleanup_stale_progress():
    stale = time.time() - main.PROGRESS_TTL_SECONDS - 10
    fresh = time.time()
    main.PROGRESS.update(
        {
            "old-finished": {"status": "finished", "updated_at": stale},
            "old-error": {"status": "error", "updated_at": stale},
            "new-finished": {"status": "finished", "updated_at": fresh},
            "old-downloading": {"status": "downloading", "updated_at": stale},
        }
    )

    main.cleanup_stale_progress()

    assert set(main.PROGRESS) == {"new-finished", "old-downloading"}
