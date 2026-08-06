# Known Failures & Limitations

Honest list of what still fails, what is unverified, and what was
inconclusive. Companion to docs/technical-debt.md (accepted debt) — this file
is about *observable failure modes*.

## Will fail today

1. **No ffmpeg on PATH → merge/remux/MP3 jobs fail mid-download** with a
   yt-dlp error in the progress area. No upfront check exists. Most likely
   real-world failure for exe users. (Fix sketch: NEXT_STEPS #1.)
2. **App restart mid-download** → job gone; UI polling the old job_id shows
   "Initializing..." forever (status `unknown` is rendered as initializing).
   The stale `.part` file remains in the download directory.
3. **Sites yt-dlp can't extract** (DRM, paywalls, unsupported) → error text
   from yt-dlp shown raw in the UI; can be cryptic for non-technical users.
4. **Browsers' directory picker cannot supply a real path** (platform
   limitation); the "Choose" button inserts only the folder *name* and warns.
   Users must type full paths. Windows-first UX debt.

## Unverified (no evidence either way)

5. **End-to-end downloads in CI.** All format-selection evidence is offline
   against synthetic catalogs through yt-dlp's real engine. A live YouTube
   download has not been run in this environment (no egress to YouTube).
   Risk: fixtures could drift from reality. Mitigation path in NEXT_STEPS #4.
6. **The PyInstaller exe.** The release workflow has never run on a real tag
   push (added this cycle, no tag exists yet). `--add-data "templates;templates"`
   syntax is Windows-correct, but the built exe is untested. First tag push
   should be treated as a test.
7. **merge_output_format=mp4 with VP9/opus source streams.** yt-dlp remuxes
   or falls back to mkv rather than failing (documented behavior), but which
   outcome users get per-video hasn't been observed end-to-end (needs ffmpeg
   + network).

## Inconclusive / negative results

8. **`threaded=True`** — claimed as an optimization in a prior commit;
   measurement showed it was already Flask's default. No-op, kept as
   documentation. (BENCHMARK_RESULTS.md §5.)
9. **FORMAT_MAP hoisting** — ~0.5 µs/call on a once-per-download call.
   Not a real optimization; the table was deleted for correctness reasons.
10. **PROGRESS race window** (concurrent sweeps deleting the same key) —
    theoretically reachable via two simultaneous `/download` requests with an
    hour-stale terminal job present; not reproduced under test. Documented
    rather than locked (docs/technical-debt.md #2).
