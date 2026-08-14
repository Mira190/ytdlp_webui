# Decisions

Record of consequential choices and their reasoning. Newest first.

## 2026-08-14 — UX/reliability pass (NEXT_STEPS items 1–4)

1. **ffmpeg check per page load, not at boot.** `has_ffmpeg()` runs in the
   `/` route (a `shutil.which` call, microseconds) so installing ffmpeg takes
   effect on refresh without restarting — better for exe users who can't
   easily restart from a terminal.
2. **Error classification server-side, translation client-side.** The server
   attaches a stable `error_kind` key (substring probes over the yt-dlp
   message, ordered specific→broad); the frontend owns the bilingual copy.
   Keeps language concerns in one place and the API language-neutral.
   Raw error text is rendered with `textContent` only — yt-dlp errors can
   embed content derived from the requested URL, so treating them as HTML
   would be an XSS vector.
3. **Live fixtures as an optional JSON overlay** (`fixtures_live.json`,
   auto-merged into `CATALOGS`) rather than regenerating `fixtures.py`:
   synthetic catalogs stay readable and reviewable; real captures can be
   committed or kept local. Confirmed this environment cannot reach YouTube
   (proxy 403), so the refresh script ships verified-but-unrun against real
   videos.
4. **Frontend gives up on `unknown` after 15 polls** (~15 s). Chosen over
   treating the first `unknown` as fatal because a just-started job can
   legitimately report `started`→hook-lag gaps; 15 s is far beyond any
   legitimate gap.

## 2026-08-06 — repository-wide review pass

1. **Replace the format table with generated fallback chains + merge
   containers** rather than patching individual table cells. The table
   encoded a false model (containers as source-stream properties); patching
   it would preserve the false model. Generated selectors keep intent (one
   `[ext=…]` preference, then capability fallbacks) in one place.
   *Rejected alternative:* passing `format_sort`/`S` options — more idiomatic
   modern yt-dlp, but a bigger behavior change and harder to pin in tests.

2. **CSRF defense via Host+Origin allowlist, not tokens.** Flask session
   tokens would work but add state and template plumbing; the Origin header
   is sufficient for the actual threat (cross-site form POST from a browser)
   and costs 25 lines. Origin-less requests stay allowed so curl/scripts
   keep working. `Origin: null` is blocked (attacker-reachable via sandboxed
   iframes; the legitimate `file://` case doesn't apply since the UI is
   served over HTTP).

3. **Fix audio-only to actually use `bestaudio/best`** and delete
   `extractaudio`/`audioformat` (CLI-era keys ignored by the Python API).
   MP3-at-192k behavior is unchanged; bandwidth drops.

4. **Cap the logger with `deque(maxlen=200)`** instead of deleting the logger
   or wiring messages into `/progress`. Keeps yt-dlp quiet, keeps a debugging
   tail available, avoids growing the API surface.

5. **Publish negative results.** Two claims from the previous pass were
   falsified by measurement (`threaded=True` no-op; hoisting negligible) and
   one introduced a real bug (TTL sweep vs timestamp-less error entries).
   Recorded in BENCHMARK_RESULTS.md §5. Policy going forward: a change may
   not be called an optimization unless a measurement accompanies it.

6. **No lock on `PROGRESS`; no job queue; keep 1 s polling; keep Tailwind
   CDN; no persistence.** For a single-user loopback tool these add surface
   without measurable benefit. Conditions to revisit each are written in
   docs/technical-debt.md.

7. **Keep the explicit `threaded=True`** despite being a default — it
   documents a load-bearing requirement (polling must not starve behind a
   download-start request) against future Flask default changes.

8. **CI runs the benchmark as a gate** (exit code = failing cells), so
   format-selection regressions fail PRs, not users.

## 2026-08-06 (earlier) — CI/CD pass
- Tag-driven release workflow (`v*.*.*` → PyInstaller exe → GitHub Release)
  mirroring the README's manual build command; `workflow_dispatch` escape
  hatch for re-releasing an existing tag.

## 2026-08-06 (earlier) — initial cleanup pass
- `requirement.txt` → `requirements.txt` (README already said plural).
- README rewritten as valid markdown.
- TTL sweep for `PROGRESS` (bug it introduced was fixed in the review pass).
