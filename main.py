import collections
import os
import threading
import time
import uuid
import webbrowser
from urllib.parse import urlsplit
from flask import Flask, render_template, request, jsonify
import yt_dlp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATES_DIR)

# Store progress data for each job_id
PROGRESS = {}

# How long a finished/errored job's progress entry is kept before being
# swept, so a long-running server doesn't accumulate one entry per download
# forever.
PROGRESS_TTL_SECONDS = 3600

# To ensure we only open a browser once
BROWSER_OPENED = False

# Height cap for each quality choice offered by the UI; "best" has no cap.
QUALITY_HEIGHTS = {"480p": 480, "720p": 720, "1080p": 1080}

# Container choices the UI offers that yt-dlp should merge/remux into.
MERGE_CONTAINERS = ("mp4", "webm", "mkv")

# Hosts this app considers "itself". The server only ever binds loopback,
# but any webpage the user visits can still form-POST to it (simple form
# POSTs need no CORS preflight), which would let an arbitrary site write
# files to arbitrary paths on this machine. POSTs are therefore rejected
# unless both the Host header and the Origin header (when a browser sends
# one) are local.
LOCAL_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}


def _is_local_hostname(netloc):
    """True if a Host header / Origin netloc refers to this machine."""
    try:
        hostname = urlsplit("//" + netloc).hostname
    except ValueError:
        return False
    return hostname in LOCAL_HOSTNAMES


@app.before_request
def reject_cross_site_posts():
    if request.method != "POST":
        return None
    origin = request.headers.get("Origin")
    if not _is_local_hostname(request.host):
        return jsonify({"status": "error",
                        "output": "Rejected: non-local Host header."}), 403
    # Non-browser clients (curl, scripts) send no Origin: allow them.
    # "null" (sandboxed/opaque origins) is attacker-reachable: block it.
    if origin is not None and (origin == "null"
                               or not _is_local_hostname(urlsplit(origin).netloc)):
        return jsonify({"status": "error",
                        "output": "Rejected: cross-site request."}), 403
    return None


class SimpleLogger:
    """
    Custom logger for yt_dlp.
    Keeps only the most recent messages: yt-dlp emits a debug line per
    fragment, so an unbounded list grows by megabytes on long downloads
    while nothing ever reads more than the tail.
    """
    MAX_MESSAGES = 200

    def __init__(self):
        self.messages = collections.deque(maxlen=self.MAX_MESSAGES)

    def debug(self, msg):
        self.messages.append("[DEBUG] " + msg)

    def warning(self, msg):
        self.messages.append("[WARNING] " + msg)

    def error(self, msg):
        self.messages.append("[ERROR] " + msg)

    def get_output(self):
        return "\n".join(self.messages)


def progress_hook_factory(job_id):
    """
    This factory creates a hook function that updates the PROGRESS dictionary
    for a specific job_id whenever yt_dlp triggers a progress event.
    """
    def hook(d):
        status = d.get("status")

        # If status is "downloading", we calculate and store progress info
        if status == "downloading":
            # Try to get total_bytes, fallback to total_bytes_estimate
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed", 0)
            eta = d.get("eta", 0)

            # Calculate percentage (clamped between 0 and 100)
            if total > 0:
                percent = min(100, max(0, int(downloaded / total * 100)))
            else:
                percent = 0

            PROGRESS[job_id] = {
                "status": "downloading",
                "downloaded_bytes": downloaded,
                "total_bytes": total,
                "speed": speed,
                "eta": eta,
                "percent": percent,
                "updated_at": time.time(),
            }

        elif status == "finished":
            # When finished, we set progress to 100
            PROGRESS[job_id] = {
                "status": "finished",
                "percent": 100,
                "eta": 0,
                "updated_at": time.time(),
            }

        elif status == "error":
            # If there is an error, store it
            PROGRESS[job_id] = {
                "status": "error",
                "error": d.get("error", "Unknown error"),
                "updated_at": time.time(),
            }

        else:
            # For other statuses (e.g. 'init'), store a basic status
            # so that the front end does not break on missing fields
            PROGRESS[job_id] = {
                "status": status or "unknown",
                "updated_at": time.time(),
            }

    return hook


def cleanup_stale_progress():
    """
    Remove finished/errored progress entries older than PROGRESS_TTL_SECONDS
    so a long-running server doesn't accumulate one entry per download forever.
    """
    cutoff = time.time() - PROGRESS_TTL_SECONDS
    stale_ids = [
        job_id for job_id, data in PROGRESS.items()
        if data.get("status") in ("finished", "error")
        and data.get("updated_at", 0) < cutoff
    ]
    for job_id in stale_ids:
        del PROGRESS[job_id]


def get_format_option(quality, audio_only, file_format):
    """
    Return a yt_dlp format selector for the given UI choices.

    Every branch ends in a fallback chain ("bestvideo+bestaudio/best/..."),
    because many videos lack a muxed format, an m4a audio track, or any
    stream in the preferred container. Container preference (mp4/webm) is
    expressed as the *first* alternative only; the actual output container
    is enforced separately via merge_output_format in download_video().
    MKV never appears in a selector: no site serves mkv source streams —
    it is purely a merge target.
    """
    if audio_only:
        return "bestaudio/best"

    height = QUALITY_HEIGHTS.get(quality)
    h = f"[height<={height}]" if height else ""

    file_format = (file_format or "").lower()
    if file_format == "mp4":
        preferred = f"bestvideo[ext=mp4]{h}+bestaudio[ext=m4a]"
    elif file_format == "webm":
        preferred = f"bestvideo[ext=webm]{h}+bestaudio[ext=webm]"
    else:
        preferred = None

    chain = [preferred] if preferred else []
    chain.append(f"bestvideo{h}+bestaudio")
    if h:
        chain.append(f"best{h}")
    chain.append("best")
    return "/".join(chain)


def download_video(job_id, url, quality, audio_only, download_dir, file_format):
    """
    This function runs in a separate thread to download a video using yt_dlp.
    It updates the PROGRESS dictionary via the progress_hook_factory.
    """
    # Create the download directory if it doesn't exist
    if download_dir and not os.path.isdir(download_dir):
        os.makedirs(download_dir, exist_ok=True)

    # Construct output template
    if download_dir:
        outtmpl = os.path.join(download_dir, "%(title)s.%(ext)s")
    else:
        outtmpl = "%(title)s.%(ext)s"

    # Determine format string
    fmt_option = get_format_option(quality, audio_only, file_format)

    ydl_opts = {
        "logger": SimpleLogger(),
        "outtmpl": outtmpl,
        "progress_hooks": [progress_hook_factory(job_id)],
    }

    # If it's audio only, set the postprocessor to extract audio as MP3
    if audio_only:
        ydl_opts.update({
            "format": fmt_option,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }],
        })
    else:
        ydl_opts["format"] = fmt_option
        # Enforce the chosen container at merge time. This is the only way
        # to get mkv output (no site serves mkv streams), and it keeps
        # mp4/webm output correct when the selector fell back to a stream
        # in a different container. yt-dlp falls back to mkv on codec
        # incompatibility rather than failing.
        if file_format and file_format.lower() in MERGE_CONTAINERS:
            ydl_opts["merge_output_format"] = file_format.lower()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        # If any exception occurs, store error status. updated_at matters:
        # cleanup_stale_progress() treats a missing timestamp as infinitely
        # old and would sweep this entry before the UI ever polls it.
        PROGRESS[job_id] = {
            "status": "error",
            "error": str(e),
            "updated_at": time.time(),
        }


@app.route('/')
def index():
    """
    Renders the main page.
    We pass quality and format options for the <select> elements in the HTML.
    """
    return render_template('index.html',
                           quality_options=["best", "480p", "720p", "1080p"],
                           format_options=["default", "mp4", "webm", "mkv"])


@app.route('/download', methods=['POST'])
def start_download():
    """
    Starts the download process in a separate thread, returns a job_id.
    """
    url = request.form.get('url', '').strip()
    if not url:
        return jsonify({"status": "error", "output": "Please provide a valid video URL."})

    cleanup_stale_progress()

    job_id = str(uuid.uuid4())

    # Initialize progress record
    PROGRESS[job_id] = {"status": "started", "percent": 0, "updated_at": time.time()}

    # Start a new thread for downloading
    threading.Thread(
        target=download_video,
        args=(
            job_id,
            url,
            request.form.get('quality', 'best'),
            request.form.get('audio_only') == 'on',
            request.form.get('download_dir', '').strip(),
            request.form.get('file_format', 'default')
        )
    ).start()

    return jsonify({"status": "started", "job_id": job_id})


@app.route('/progress', methods=['GET'])
def get_progress():
    """
    Queries the PROGRESS dictionary for the current status of the given job_id.
    """
    job_id = request.args.get('job_id', '')
    return jsonify(PROGRESS.get(job_id, {"status": "unknown"}))


def open_browser():
    """
    Optionally opens the default browser. We make sure it only opens once.
    """
    global BROWSER_OPENED
    if not BROWSER_OPENED:
        BROWSER_OPENED = True
        webbrowser.open("http://127.0.0.1:5000/")


if __name__ == '__main__':
    # Automatically open the browser after 1.5 seconds (optional)
    threading.Timer(1.5, open_browser).start()
    app.run(debug=False, threaded=True)
