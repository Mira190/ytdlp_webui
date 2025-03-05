📺 YT-DLP Web UI - Video Downloader

🚀 A simple and user-friendly YouTube video downloader with a modern web UI, powered by Flask & yt-dlp.

✅ Features:

📥 Download YouTube videos in different formats (MP4, WebM, MKV)
🎵 Extract audio (MP3 format)
📺 Select video resolution (480p, 720p, 1080p)
🚀 Real-time progress display with percentage & ETA
🌍 Multi-language support (English & Chinese)
📁 Choose download directory
🎯 Simply enter the video URL, select format & resolution, and click "Start Download" – it's that easy!

📥 Download & Run

Method 1️⃣: Run the EXE (No Installation Required)
📌 For Windows users – just download and run!

📥 Download yt-dlp-webui.exe (Latest Version)

Double-click yt-dlp-webui.exe

Enter the YouTube video URL, choose format & resolution, and start downloading! 🚀

🛠️ How to Run Locally

Install Python dependencies:
bash
Copy
Edit
pip install -r requirements.txt
Start the Flask server:
bash
Copy
Edit
python main.py
Open your browser and go to:
cpp
Copy
Edit
http://127.0.0.1:5000
🛠️ Build Windows EXE
If you want to create a standalone .exe, run:

bash
Copy
Edit
pyinstaller --onefile --add-data "templates;templates" main.py
The generated executable will be in the dist/ folder.

🌟 Features

✅ Download YouTube videos (MP4, WebM, MKV)
✅ Supports 480p / 720p / 1080p resolutions
✅ Extract audio as MP3
✅ Real-time progress tracking
✅ Choose download directory
✅ Multi-language support (English & Chinese)

📸 Screenshots

🎨 Web UI 📥 Download Progress
📌 Troubleshooting

1. EXE doesn’t open?
   Your antivirus might be blocking it. Try adding an exception for yt-dlp-webui.exe.
2. install.bat can't find Python?
   Install Python manually from python.org and try again.
3. No progress updates during download?
   Update yt-dlp by running:
   bash
   Copy
   Edit
   pip install --upgrade yt-dlp
   📜 License
   This project is open-source and licensed under the MIT License.

If you find this project helpful, please ⭐ Star this repository! 🚀

📌 Contributing
👨‍💻 Developer: @mirawu
📧 Contact: [mirawu190@gmail.com]

🚀 Try It Now!
📥 Download yt-dlp-webui.exe (Latest Version) 🚀
