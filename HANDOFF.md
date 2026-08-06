# HANDOFF

Everything a new contributor (human or model) needs to continue **without
rereading the whole repository**. Trust this file; verify with the commands
in §Verify.

## What this project is

Local single-user web UI for yt-dlp. One Flask file (`main.py`, ~320 lines),
one template (`templates/index.html`), distributed as `python main.py` or a
PyInstaller Windows exe. Binds 127.0.0.1:5000, auto-opens the browser.
Audience: non-technical Windows users. Full picture: `docs/architecture.md`.

## Repo map (complete)

| Path | What it is |
|---|---|
| `main.py` | The entire backend. Routes: `GET /` (page), `POST /download` (spawns download thread, returns `job_id`), `GET /progress?job_id=` (poll). Module-level: `PROGRESS` job dict, TTL sweep, origin guard, `get_format_option`, `download_video`, `SimpleLogger` |
| `templates/index.html` | The entire frontend: Tailwind CDN, vanilla JS, en/zh i18n dict, 1 s polling loop |
| `tests/test_app.py` | 68 offline tests (pytest). Run in 2.5 s |
| `benchmarks/fixtures.py` | Synthetic format catalogs (3 video classes) |
| `benchmarks/run_format_bench.py` | Evaluates every UI choice through yt-dlp's real selector, offline. Exit code = failing cells |
| `benchmarks/results/` | `baseline-2d6f640.md` (24/51 pass) and `improved.md` (51/51) |
| `.github/workflows/ci.yml` | pyflakes + pytest + benchmark on push/PR to main |
| `.github/workflows/release.yml` | Tag `v*.*.*` → Windows exe → GitHub Release. **Never yet exercised** |
| `requirements.txt` | `Flask>=2.0.0`, `yt-dlp>=2021.12.1` (dev also: pytest, pyflakes) |
| Docs | `docs/{architecture,critical-review,evaluation-methodology,technical-debt}.md`, `BENCHMARK_RESULTS.md`, `DECISIONS.md`, `KNOWN_FAILURES.md`, `NEXT_STEPS.md` |

## State of play (2026-08-06)

- Branch `claude/repo-optimization-q85rs0`; PRs #1 and #2 already merged to
  `main`; this review/hardening pass is pushed on top. CI green locally.
- This pass fixed, with tests and measurements: format selection (24/51 →
  51/51 UI combinations working — the big one), cross-site POST guard,
  audio-only downloading full video, error entries being swept before read,
  unbounded logger memory. Details: `docs/critical-review.md`;
  numbers: `BENCHMARK_RESULTS.md`.

## Invariants — do not break

1. **Every format selector must end in a fallback chain** (`…/bestvideo…+bestaudio/best`).
   Never emit `[ext=mkv]` in a selector (mkv is a merge target, not a source).
   CI's benchmark gate enforces this (any cell failing → red).
2. **POSTs must pass the Host+Origin guard**; Origin-less requests stay
   allowed (scripts), `Origin: null` stays blocked.
3. **Every `PROGRESS` entry needs `updated_at`** or the TTL sweep may delete
   it instantly (this bug already happened once).
4. **Tests must stay offline** — CI has no YouTube egress. Use the fixture
   catalogs; extend `benchmarks/fixtures.py` for new video classes.
5. Don't call something an optimization without a measurement
   (`DECISIONS.md` #5 — two prior claims were falsified).

## Verify (from a clean checkout)

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt pytest pyflakes
venv/bin/python -m pyflakes main.py tests benchmarks   # clean
venv/bin/python -m pytest tests/ -q                    # 68 passed
venv/bin/python benchmarks/run_format_bench.py         # 51/51, exit 0
venv/bin/python main.py                                # serves 127.0.0.1:5000
```

## Where to work next

`NEXT_STEPS.md` is the ranked queue. Top item: startup ffmpeg check
(~15 lines, addresses the most likely real-user failure). Each item lists its
test strategy. `KNOWN_FAILURES.md` lists what's unverified (notably: the
release workflow has never run — first tag push is a test; and no end-to-end
download has run in CI's offline environment).

## Gotchas that cost time

- `yt_dlp.YoutubeDL.process_ie_result(info, download=False)` with
  `simulate=True` is the way to test selection offline; it raises
  `ExtractorError` (subclass chain differs from `DownloadError` — catch
  `yt_dlp.utils.YoutubeDLError`).
- Flask's dev server is threaded **by default** since 1.0; don't "add"
  threading as a fix.
- `extractaudio`/`audioformat` are CLI option names; the Python API ignores
  them silently. Use `postprocessors=[{"key": "FFmpegExtractAudio", …}]`.
- The GitHub `gh` CLI is unavailable in the remote dev environment; use the
  GitHub MCP tools. Pushes to `claude/*` branches only.
