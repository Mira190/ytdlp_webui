# Known Failures & Limitations

Honest list of what still fails, what is unverified, and what was
inconclusive. Companion to docs/technical-debt.md (accepted debt) — this file
is about *observable failure modes*.

## Will fail today

1. **No ffmpeg on PATH → merge/remux/MP3 jobs still fail**, but the UI now
   warns upfront (bilingual banner on page load, re-checked per refresh) and
   the mid-download error is classified to a clear "install ffmpeg" message.
   The failure itself remains until ffmpeg is bundled with the exe
   (NEXT_STEPS #2).
2. **App restart mid-download** → job gone; the UI now gives up after ~15
   polls with a bilingual "job not found — app may have been restarted"
   message instead of showing "Initializing..." forever. The stale `.part`
   file still remains in the download directory.
3. **Sites yt-dlp can't extract** (DRM, paywalls, unsupported) → now mapped
   to short bilingual messages (unsupported URL / DRM / format unavailable /
   network / ffmpeg), with the raw yt-dlp text in a collapsible details
   block. Unrecognized errors still show raw text.
4. **Browsers' directory picker cannot supply a real path** (platform
   limitation); the "Choose" button inserts only the folder *name* and warns.
   Users must type full paths. Windows-first UX debt.

## Unverified (no evidence either way)

5. **End-to-end downloads in CI.** All format-selection evidence is offline
   against synthetic catalogs through yt-dlp's real engine. A live YouTube
   download has not been run in this environment — confirmed empirically
   2026-08-14: `refresh_fixtures.py` fails with a proxy 403 on YouTube API
   tunnels. The script is ready to close the fixtures-drift gap on any
   network-enabled machine (NEXT_STEPS #1).
5a. ~~New frontend flows are browser-untested~~ — **verified 2026-08-14** in
   headless Chromium (Playwright): banner en/zh toggle, friendly error +
   details block on a real failed download, job-not-found after 15 polls
   with polling confirmed stopped, submit button re-enabled in both paths
   (11/11 checks). Bonus confirmation: with the CDN unreachable the page
   rendered unstyled but fully functional — the graceful degradation
   docs/technical-debt.md #4 predicted.
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
    hour-stale terminal job present; not reproduced under test. The sweep now
    uses `PROGRESS.pop(job_id, None)`, removing the KeyError failure mode;
    the (harmless) hook-re-adds-after-sweep interleaving remains documented
    in docs/technical-debt.md #2.
