import os
import threading
import uuid
import webbrowser
from flask import Flask, render_template, request, jsonify
import yt_dlp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATES_DIR)

# Store progress data for each job_id
PROGRESS = {}

# To ensure we only open a browser once
BROWSER_OPENED = False

class SimpleLogger:
    """
    Custom logger for yt_dlp.
    We append debug, warning, error messages for reference if needed.
    """
    def __init__(self):
        self.messages = []

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
            }

        elif status == "finished":
            # When finished, we set progress to 100
            PROGRESS[job_id] = {
                "status": "finished",
                "percent": 100,
                "eta": 0
            }

        elif status == "error":
            # If there is an error, store it
            PROGRESS[job_id] = {
                "status": "error",
                "error": d.get("error", "Unknown error")
            }

        else:
            # For other statuses (e.g. 'init'), store a basic status
            # so that the front end does not break on missing fields
            PROGRESS[job_id] = {
                "status": status or "unknown"
            }

    return hook


def get_format_option(quality, audio_only, file_format):
    """
    Return a suitable yt_dlp format string based on:
    - quality (best, 480p, 720p, 1080p)
    - audio_only
    - file_format (default, mp4, webm, mkv, etc.)
    """
    if audio_only:
        return "bestaudio"

    mapping = {
        "mp4": {
            "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "480p": "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]",
            "720p": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]",
            "1080p": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]"
        },
        "webm": {
            "best": "bestvideo[ext=webm]+bestaudio/best[ext=webm]",
            "480p": "bestvideo[ext=webm][height<=480]+bestaudio/best[ext=webm]",
            "720p": "bestvideo[ext=webm][height<=720]+bestaudio/best[ext=webm]",
            "1080p": "bestvideo[ext=webm][height<=1080]+bestaudio/best[ext=webm]"
        },
        "mkv": {
            "best": "bestvideo[ext=mkv]+bestaudio/best[ext=mkv]",
            "480p": "bestvideo[ext=mkv][height<=480]+bestaudio/best[ext=mkv]",
            "720p": "bestvideo[ext=mkv][height<=720]+bestaudio/best[ext=mkv]",
            "1080p": "bestvideo[ext=mkv][height<=1080]+bestaudio/best[ext=mkv]"
        },
        "default": {
            "best": "best",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        }
    }
    return mapping.get(file_format.lower(), mapping["default"]).get(quality, "best")


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
            "extractaudio": True,
            "audioformat": "mp3",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }],
        })
    else:
        ydl_opts["format"] = fmt_option

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        # If any exception occurs, store error status
        PROGRESS[job_id] = {
            "status": "error",
            "error": str(e)
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

    job_id = str(uuid.uuid4())

    # Initialize progress record
    PROGRESS[job_id] = {"status": "started", "percent": 0}

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
    app.run(debug=False)
