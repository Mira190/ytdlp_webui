# Next Steps

Ranked by user value ÷ implementation cost. Items below the cut line were
judged not worth their cost this cycle — with the result that would change
that judgment.

## Above the line (do next)

1. **Run `benchmarks/refresh_fixtures.py` on a network-enabled machine** and
   optionally commit `fixtures_live.json` so CI covers real catalogs. The
   script exists and its merge path is verified with synthetic data; the dev
   environment has no YouTube egress (proxy 403), so it has never run against
   real videos.
2. **Exercise the release workflow once** (push tag `v1.0.0`, download the
   exe, run it on Windows). Until then the exe path is unverified
   (KNOWN_FAILURES #6). While there, decide whether to bundle ffmpeg with the
   exe — the UI now warns when it's missing, but bundling would remove the
   failure mode entirely for exe users.
3. **Manual browser pass over the new frontend paths** (ffmpeg banner
   language toggle, error details block, job-not-found timeout). They are
   JS-syntax-checked and server-side tested, but no real browser has
   exercised the DOM flows.

## Done since the ranking was written (2026-08-14)

- ~~Startup ffmpeg check~~ — banner in `index.html`, bilingual, re-checked
  per page load; tested.
- ~~Surface yt-dlp errors helpfully~~ — `classify_download_error` →
  `error_kind` in progress payloads; frontend shows translated message with
  raw text in a `<details>` block (rendered via `textContent`, never HTML).
- ~~Prolonged `unknown` handling~~ — polling stops after 15 unknown polls
  with a bilingual "job not found" message.
- ~~Fixture refresh script~~ — written + merge path verified; live run
  blocked by environment (see #1 above).
- ~~`PROGRESS.pop` hardening~~ — sweep no longer able to KeyError under
  concurrent sweeps (was technical-debt #2's cheap mitigation).

## Below the line (explicitly deferred)

- **Download queue / concurrency cap** — one user, one form, button disables
  while running. Do it when playlists land.
- **SSE instead of polling** — 1 req/s local traffic; no measurable benefit.
- **Vendored CSS replacing Tailwind CDN** — do it only if offline use becomes
  a goal; hand-write ~100 lines rather than vendoring Tailwind.
- **Playlist support, download history, cookies-for-membership-content** —
  real features, need product direction first.
- **Type checking (mypy)** — 320 annotated-free lines; pyflakes + tests cover
  the failure classes seen so far. Reconsider if the codebase grows beyond a
  few files.

## Standing policy

Any PR claiming performance or reliability improvement must include a
measurement (see docs/evaluation-methodology.md). CI enforces: pyflakes,
68-test suite, format benchmark exit code 0.
