import logging
import os
import shutil
import threading
import time
import uuid
import webbrowser

import yt_dlp
from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

# The server can write to arbitrary local paths, so it only ever listens on
# the loopback interface. The host is intentionally not configurable.
HOST = "127.0.0.1"
DEFAULT_PORT = 5000


def read_port(value):
    """Parse a port from the environment, falling back to DEFAULT_PORT."""
    try:
        port = int(value)
        if 1 <= port <= 65535:
            return port
    except (TypeError, ValueError):
        pass
    logging.getLogger(__name__).warning(
        "Ignoring invalid YTDLP_WEBUI_PORT=%r, using %d", value, DEFAULT_PORT
    )
    return DEFAULT_PORT


PORT = read_port(os.environ.get("YTDLP_WEBUI_PORT", DEFAULT_PORT))

DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

# ffmpeg is needed for merging separate video/audio streams and for MP3
# extraction. Detected once at startup; only used to warn in the UI.
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

QUALITY_OPTIONS = ("best", "480p", "720p", "1080p")
FORMAT_OPTIONS = ("default", "mp4", "webm", "mkv")
QUALITY_HEIGHTS = {"480p": 480, "720p": 720, "1080p": 1080}

# Progress data for each job_id. Written by download threads and read/swept
# by request threads, so every access goes through PROGRESS_LOCK.
PROGRESS = {}
PROGRESS_LOCK = threading.Lock()

# How long a finished/errored job's progress entry is kept before being
# swept, so a long-running server doesn't accumulate one entry per download
# forever.
PROGRESS_TTL_SECONDS = 3600

YTDLP_LOGGER = logging.getLogger("ytdlp_webui.yt_dlp")


def set_progress(job_id, **fields):
    """
    Record progress for job_id under the lock. Always stamps updated_at.
    Fields are merged into the existing entry so context such as the
    filename survives status transitions.
    """
    fields["updated_at"] = time.time()
    with PROGRESS_LOCK:
        PROGRESS.setdefault(job_id, {}).update(fields)


def get_progress_snapshot(job_id):
    """Return a copy of job_id's progress entry, or None if unknown."""
    with PROGRESS_LOCK:
        data = PROGRESS.get(job_id)
        return dict(data) if data is not None else None


def cleanup_stale_progress():
    """
    Remove finished/errored progress entries older than PROGRESS_TTL_SECONDS
    so a long-running server doesn't accumulate one entry per download forever.
    """
    cutoff = time.time() - PROGRESS_TTL_SECONDS
    with PROGRESS_LOCK:
        stale_ids = [
            job_id
            for job_id, data in PROGRESS.items()
            if data.get("status") in ("finished", "error") and data.get("updated_at", 0) < cutoff
        ]
        for job_id in stale_ids:
            del PROGRESS[job_id]


def progress_hook_factory(job_id):
    """
    Create a yt_dlp progress hook for job_id.

    yt_dlp reports "finished" once per downloaded file (e.g. separately for
    the video and audio streams before they are merged), so "finished" here
    only means "processing"; the job is marked finished by download_video
    once ydl.download() has returned.
    """

    def hook(d):
        status = d.get("status")

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0

            # Calculate percentage (clamped between 0 and 100)
            if total > 0:
                percent = min(100, max(0, int(downloaded / total * 100)))
            else:
                percent = 0

            set_progress(
                job_id,
                status="downloading",
                percent=percent,
                downloaded_bytes=downloaded,
                total_bytes=total,
                speed=d.get("speed") or 0,
                eta=d.get("eta") or 0,
                filename=os.path.basename(d.get("filename") or ""),
            )

        elif status == "finished":
            set_progress(job_id, status="processing", percent=100)

    return hook


def postprocessor_hook_factory(job_id):
    """
    Create a yt_dlp postprocessor hook for job_id. yt_dlp sends "started"
    and "finished" for each postprocessor (merger, audio extraction, ...).
    """

    def hook(d):
        status = d.get("status")
        if status == "started":
            set_progress(job_id, status="processing", postprocessor=d.get("postprocessor"))
        elif status == "finished":
            # The postprocessor's output (e.g. the merged file) is the name
            # the user will find on disk, unlike the per-stream fragments.
            filepath = (d.get("info_dict") or {}).get("filepath")
            if filepath:
                set_progress(job_id, filename=os.path.basename(filepath))

    return hook


def build_format_options(quality, audio_only, file_format, ffmpeg_available=None):
    """
    Return the format-related yt_dlp options to merge into ydl_opts for the
    given quality (see QUALITY_OPTIONS), audio_only flag and file_format
    (see FORMAT_OPTIONS).

    Without ffmpeg, yt_dlp cannot merge separate video and audio streams and
    aborts if asked to, so in that case only single-file ("progressive")
    formats are requested. ffmpeg_available defaults to FFMPEG_AVAILABLE.
    """
    if ffmpeg_available is None:
        ffmpeg_available = FFMPEG_AVAILABLE

    if audio_only:
        return {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

    height = QUALITY_HEIGHTS.get(quality)
    h = f"[height<={height}]" if height else ""

    if not ffmpeg_available:
        if file_format in ("mp4", "webm"):
            return {"format": f"best[ext={file_format}]{h}/best{h}"}
        return {"format": f"best{h}"}

    # The fallback selectors may pick codecs the preferred container cannot
    # hold (e.g. VP9+Opus for mp4), so mkv is listed as the second choice:
    # yt_dlp uses the first listed extension compatible with the streams.
    if file_format == "mp4":
        return {
            "format": f"bestvideo[ext=mp4]{h}+bestaudio[ext=m4a]/bestvideo{h}+bestaudio/best{h}",
            "merge_output_format": "mp4/mkv",
        }
    if file_format == "webm":
        return {
            "format": f"bestvideo[ext=webm]{h}+bestaudio[ext=webm]/bestvideo{h}+bestaudio/best{h}",
            "merge_output_format": "webm/mkv",
        }
    if file_format == "mkv":
        return {
            "format": f"bestvideo{h}+bestaudio/best{h}",
            "merge_output_format": "mkv",
        }
    return {"format": f"bestvideo{h}+bestaudio/best{h}"}


def download_video(job_id, url, quality, audio_only, download_dir, file_format):
    """
    Download url with yt_dlp. Runs in a separate thread and reports progress
    through set_progress(). The download directory must already exist.
    """
    # Everything is inside the try so that no failure can leave the job
    # stuck at "started" with the UI polling forever.
    try:
        ydl_opts = {
            "logger": YTDLP_LOGGER,
            "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "progress_hooks": [progress_hook_factory(job_id)],
            "postprocessor_hooks": [postprocessor_hook_factory(job_id)],
        }
        ydl_opts.update(build_format_options(quality, audio_only, file_format))
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:  # includes yt_dlp.utils.DownloadError
        set_progress(job_id, status="error", error=str(e))
        return

    set_progress(job_id, status="finished", percent=100, eta=0)


def error_response(message, code=400):
    return jsonify({"status": "error", "output": message}), code


def is_cross_site_request(req):
    """
    True if a browser sent req from another site. The server only listens on
    loopback, but any web page the user visits can still make the browser
    POST to it, so /download must reject requests that don't come from the
    app's own origin. Non-browser clients send neither header and are allowed.
    """
    fetch_site = req.headers.get("Sec-Fetch-Site")
    if fetch_site and fetch_site not in ("same-origin", "none"):
        return True
    origin = req.headers.get("Origin")
    return bool(origin) and origin != req.host_url.rstrip("/")


@app.route("/")
def index():
    """
    Renders the main page.
    We pass quality and format options for the <select> elements in the HTML.
    """
    return render_template(
        "index.html",
        quality_options=QUALITY_OPTIONS,
        format_options=FORMAT_OPTIONS,
        default_download_dir=DEFAULT_DOWNLOAD_DIR,
        ffmpeg_available=FFMPEG_AVAILABLE,
    )


@app.route("/download", methods=["POST"])
def start_download():
    """
    Validates the request, starts the download in a background thread and
    returns its job_id.
    """
    if is_cross_site_request(request):
        return error_response("Cross-site requests are not allowed.", 403)

    url = request.form.get("url", "").strip()
    quality = request.form.get("quality", "best")
    file_format = request.form.get("file_format", "default")
    audio_only = request.form.get("audio_only") == "on"
    download_dir = request.form.get("download_dir", "").strip() or DEFAULT_DOWNLOAD_DIR
    download_dir = os.path.abspath(os.path.expanduser(download_dir))

    if not url:
        return error_response("Please provide a valid video URL.")
    if not url.startswith(("http://", "https://")):
        return error_response("URL must start with http:// or https://")
    if quality not in QUALITY_OPTIONS:
        return error_response(f"Invalid quality: {quality}")
    if file_format not in FORMAT_OPTIONS:
        return error_response(f"Invalid file format: {file_format}")
    if audio_only and not FFMPEG_AVAILABLE:
        return error_response("ffmpeg is required for MP3 extraction but was not found.")

    try:
        os.makedirs(download_dir, exist_ok=True)
    except OSError as e:
        return error_response(f"Cannot create download directory: {e}")

    cleanup_stale_progress()

    job_id = str(uuid.uuid4())
    set_progress(job_id, status="started", percent=0)

    threading.Thread(
        target=download_video,
        args=(job_id, url, quality, audio_only, download_dir, file_format),
        name=f"download-{job_id[:8]}",
        daemon=True,
    ).start()

    return jsonify({"status": "started", "job_id": job_id})


@app.route("/progress", methods=["GET"])
def get_progress():
    """Returns the current progress entry for the given job_id."""
    job_id = request.args.get("job_id", "")
    data = get_progress_snapshot(job_id)
    if data is None:
        return jsonify({"status": "unknown"}), 404
    return jsonify(data)


def open_browser():
    """Opens the web UI in the default browser."""
    webbrowser.open(f"http://{HOST}:{PORT}/")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if os.environ.get("YTDLP_WEBUI_NO_BROWSER") != "1":
        # Open the browser once the server has had a moment to start.
        threading.Timer(1.5, open_browser).start()
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
