# Architecture

## What this project actually is

A **local, single-user desktop tool** with a browser UI: a ~320-line Flask app
wrapping yt-dlp, distributed two ways — `python main.py` or a PyInstaller
Windows exe. It binds loopback only, opens the user's browser on launch, and
writes downloads to a user-chosen directory on the same machine.

**Users:** primarily non-technical Windows users who run the exe.
**Success criterion:** paste URL → pick quality/format → get a playable file,
with visible progress, without touching a terminal.

## Core assumptions (and their status)

| Assumption | Status |
|---|---|
| Single user, same machine as browser | Holds; the design leans on it (loopback bind, local paths in the form) |
| Downloads are long-running → need async + polling | Holds |
| Local-only bind makes the server unreachable by attackers | **False** as originally built — any webpage can form-POST to loopback; mitigated by the Origin/Host guard in `main.py` |
| yt-dlp format strings from 2021 still select formats | **False** — measured 27/51 UI combinations failing before the 2026 fix (see BENCHMARK_RESULTS.md) |
| ffmpeg is available | Unverified at runtime; merging/remuxing/MP3 extraction all require it. Not bundled in the exe. See technical-debt.md |

## Components

```
browser (templates/index.html: Tailwind CDN + vanilla JS, zh/en i18n)
   │  POST /download (form)          → {job_id}
   │  GET  /progress?job_id=… (1s poll) → {status, percent, speed, eta}
   ▼
main.py (Flask, threaded dev server)
   ├── reject_cross_site_posts()   before_request guard: Host+Origin must be local
   ├── start_download()            validates URL presence, spawns daemonless Thread
   ├── download_video()  [thread]  builds ydl_opts, runs yt_dlp.YoutubeDL.download
   │      ├── get_format_option()  UI choices → selector string with fallback chain
   │      ├── merge_output_format  enforces mp4/webm/mkv container at merge time
   │      ├── SimpleLogger         ring buffer (deque maxlen=200)
   │      └── progress_hook        writes PROGRESS[job_id]
   ├── PROGRESS dict               in-memory job store; TTL sweep on new downloads
   └── open_browser()              once, 1.5s after start
```

## State & concurrency model

- All state is the in-process `PROGRESS` dict; nothing persists across restarts.
  Restarting the app mid-download abandons the job (yt-dlp's `.part` files allow
  manual resume by re-downloading to the same directory).
- One thread per download, unlimited. Dict writes are single assignments
  (atomic under the GIL); the TTL sweep snapshots keys before deleting. No lock
  is used — see DECISIONS.md for why that's accepted at this scale.
- The Flask dev server (threaded by default since Flask 1.0) serves the poll
  requests; there is no WSGI production server because the audience is one
  local user.

## Is this the simplest reliable architecture for the goal?

Mostly yes. Flask + one template + threads + polling is appropriate for a
single-user local tool; SSE/websockets, a job queue, or a database would add
operational surface without user-visible benefit. The two places where the
architecture was *simpler than correct* were format selection (fixed: fallback
chains + merge containers) and the unguarded loopback POST (fixed: origin
guard). The remaining known simplifications-that-cost are catalogued in
technical-debt.md; none currently justify structural change.
