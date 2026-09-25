# 📺 YT-DLP Web UI - Video Downloader

🚀 A simple and user-friendly YouTube video downloader with a modern web UI, powered by Flask & yt-dlp.

## ✅ Features

- 📥 Download YouTube videos in different formats (MP4, WebM, MKV)
- 🎵 Extract audio (MP3 format)
- 📺 Select video resolution (480p, 720p, 1080p)
- 🚀 Real-time progress display with percentage & ETA
- 🌍 Multi-language support (English & Chinese)
- 📁 Custom download directory (defaults to `~/Downloads`)
- 🎯 Simply enter the video URL, select format & resolution, and click "Start Download" – it's that easy!

## 📋 Requirements

- **Python ≥ 3.11** (only when running from source)
- **ffmpeg** on your `PATH`. It is needed for MP3 extraction and for merging
  separate video and audio streams. Without it the web UI shows a warning and
  only single-file video formats are requested, which usually caps quality at
  720p. Install it with one of:

  ```bash
  winget install Gyan.FFmpeg      # Windows (or: choco install ffmpeg)
  brew install ffmpeg             # macOS
  sudo apt install ffmpeg         # Debian / Ubuntu
  ```

## 📥 Download & Run

### Method 1️⃣: Run the EXE (No Installation Required)

📌 For Windows users – just download and run!

📥 Download `yt-dlp-webui.exe` (Latest Version)

1. Double-click `yt-dlp-webui.exe`
2. Enter the YouTube video URL, choose format & resolution, and start downloading! 🚀

### 🛠️ Method 2️⃣: Run Locally

Create a virtual environment and install the Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Start the Flask server:

```bash
python main.py
```

Your browser opens automatically at:

```
http://127.0.0.1:5000
```

The server only listens on `127.0.0.1`. Files are saved to `~/Downloads` unless
you enter another directory in the form. Optional environment variables:

| Variable | Default | Effect |
|----------|---------|--------|
| `YTDLP_WEBUI_PORT` | `5000` | Port to listen on |
| `YTDLP_WEBUI_NO_BROWSER` | unset | Set to `1` to not open the browser on startup |

```bash
YTDLP_WEBUI_PORT=8080 YTDLP_WEBUI_NO_BROWSER=1 python main.py
```

## 🛠️ Build Windows EXE

If you want to create a standalone `.exe`, run:

```bash
pyinstaller --onefile --name yt-dlp-webui --add-data "templates;templates" --add-data "static;static" main.py
```

The generated `yt-dlp-webui.exe` will be in the `dist/` folder. (On macOS/Linux,
use `:` instead of `;` in the `--add-data` arguments.)

## 🧪 Development

```bash
pip install -r requirements-dev.txt
pytest
ruff check . && ruff format --check .
```

The tests fake yt-dlp, so they need neither network access nor ffmpeg.

## 🚀 Releasing

Releases are automated. Pushing a tag matching `v*.*.*` (e.g. `v1.2.0`) triggers
[`.github/workflows/release.yml`](.github/workflows/release.yml), which builds
`yt-dlp-webui.exe` with PyInstaller and publishes it as a GitHub Release asset:

```bash
git tag v1.2.0
git push origin v1.2.0
```

Every push/PR to `main` also runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
(ruff lint/format checks and the pytest suite on Python 3.11 and 3.12), so breakage
is caught before a release is cut.

## 📌 Troubleshooting

1. **EXE doesn't open?**
   Your antivirus might be blocking it. Try adding an exception for `yt-dlp-webui.exe`.
2. **Download completes but there is no merged file / audio is not converted to MP3?**
   ffmpeg is missing. Install it (see [Requirements](#-requirements)) and make sure
   it is on your `PATH`, then restart the app.
3. **No progress updates during download?**
   Update yt-dlp by running:
   ```bash
   pip install --upgrade yt-dlp
   ```

## 📜 License

This project is open-source and licensed under the MIT License.

If you find this project helpful, please ⭐ star this repository!

## 📌 Contributing

👨‍💻 Developer: @mirawu
📧 Contact: mirawu190@gmail.com
