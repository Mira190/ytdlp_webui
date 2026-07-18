# 📺 YT-DLP Web UI - Video Downloader

🚀 A simple and user-friendly YouTube video downloader with a modern web UI, powered by Flask & yt-dlp.

## ✅ Features

- 📥 Download YouTube videos in different formats (MP4, WebM, MKV)
- 🎵 Extract audio (MP3 format)
- 📺 Select video resolution (480p, 720p, 1080p)
- 🚀 Real-time progress display with percentage & ETA
- 🌍 Multi-language support (English & Chinese)
- 📁 Choose download directory
- 🎯 Simply enter the video URL, select format & resolution, and click "Start Download" – it's that easy!

## 📥 Download & Run

### Method 1️⃣: Run the EXE (No Installation Required)

📌 For Windows users – just download and run!

📥 Download `yt-dlp-webui.exe` (Latest Version)

1. Double-click `yt-dlp-webui.exe`
2. Enter the YouTube video URL, choose format & resolution, and start downloading! 🚀

### 🛠️ Method 2️⃣: Run Locally

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Start the Flask server:

```bash
python main.py
```

Open your browser and go to:

```
http://127.0.0.1:5000
```

## 🛠️ Build Windows EXE

If you want to create a standalone `.exe`, run:

```bash
pyinstaller --onefile --add-data "templates;templates" main.py
```

The generated executable will be in the `dist/` folder.

## 🚀 Releasing

Releases are automated. Pushing a tag matching `v*.*.*` (e.g. `v1.2.0`) triggers
[`.github/workflows/release.yml`](.github/workflows/release.yml), which builds
`yt-dlp-webui.exe` with PyInstaller and publishes it as a GitHub Release asset:

```bash
git tag v1.2.0
git push origin v1.2.0
```

Every push/PR to `main` also runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml),
a quick compile/import sanity check, so breakage is caught before a release is cut.

## 📌 Troubleshooting

1. **EXE doesn't open?**
   Your antivirus might be blocking it. Try adding an exception for `yt-dlp-webui.exe`.
2. **install.bat can't find Python?**
   Install Python manually from python.org and try again.
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
