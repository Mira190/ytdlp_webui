# Technical Debt

Deliberately-accepted debt, ranked by (risk × likelihood). Each entry says why
it's accepted now and what would change that call.

## 1. ffmpeg is warned about, but not bundled
The UI now shows a bilingual banner when `shutil.which("ffmpeg")` finds
nothing (re-checked per page load), and mid-download ffmpeg errors are
classified to a clear message — but merge/remux/MP3 jobs still *fail* on
machines without ffmpeg, and the PyInstaller exe does not bundle it (~80 MB).
**Accepted because:** bundling is a release-size product decision.
**Revisit when:** the release workflow is first exercised (NEXT_STEPS #2) —
that's the natural moment to decide.

## 2. `PROGRESS` has no lock
Writers: download threads (single dict-item assignments, atomic under the
GIL). Sweeper: `cleanup_stale_progress` snapshots matching ids, then removes
them with `PROGRESS.pop(job_id, None)` — concurrent sweeps can no longer
raise. Remaining worst interleaving: a hook re-adds a job after the sweep
removed it (needs a >1h-stale timestamp on a still-writing job — effectively
impossible, and harmless: the entry just reappears until the next sweep).
**Accepted because:** single local user; no observable failure mode left.
**Revisit when:** anything makes this multi-user.

## 3. Progress entries survive only in memory
Restarting the app forgets all jobs; the UI polling an old `job_id` shows
"Initializing..." forever (status `unknown`). **Accepted because:** local tool,
user restarts and retries; yt-dlp `.part` files resume transparently on
re-download. **Revisit when:** users report confusion; the cheap UI fix is
treating `unknown` as an error after N polls (NEXT_STEPS #3).

## 4. Tailwind loaded from CDN
Offline or CDN-blocked users get an unstyled but functional form. Also a
(read-only) external dependency at every launch. **Accepted because:** vendoring
Tailwind properly means a build step, which this project pointedly avoids.
**Revisit when:** offline use becomes a stated goal — then vendor a small
hand-written CSS file instead (the page uses a tiny fraction of Tailwind).

## 5. Unlimited concurrent downloads
Every POST spawns a thread; 20 rapid submissions = 20 parallel yt-dlp runs
fighting for bandwidth. **Accepted because:** the only submitter is the page's
single form, which disables its button while a job runs. **Revisit when:**
playlist support or a queue UI is added.

## 6. `job_id` accepted without validation on `/progress`
Read-only endpoint returning job status for guessable-only-by-UUID keys; no
information of value to an attacker (and GETs are origin-unguarded by design).
**Accepted because:** nothing sensitive is exposed. **Revisit when:** progress
payloads start carrying filenames/paths — then either guard GETs or strip
paths.

## 7. Frontend i18n dictionary duplicates label text in the template
`index.html` hardcodes English labels *and* repeats them in the JS `i18n.en`
map; `setLanguage` immediately overwrites the static text. Harmless
duplication (~20 lines). New strings added in 2026-08-14 (banner, error
kinds, job-not-found) live only in the dictionary, so the duplication no
longer grows. **Revisit when:** a third language is added — then render all
labels from the dictionary only.

## Paid off in this pass
- 2021-era format table (deleted; was broken for 27/51 combinations).
- Dead `extractaudio`/`audioformat` keys (CLI-only names, ignored by the API).
- Unbounded logger buffer (now `deque(maxlen=200)`).
- Missing `updated_at` on error entries (fresh errors were sweepable).
- No tests / no lint (now 68 tests + pyflakes in CI, both green).
