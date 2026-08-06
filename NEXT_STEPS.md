# Next Steps

Ranked by user value ÷ implementation cost. Items below the cut line were
judged not worth their cost this cycle — with the result that would change
that judgment.

## Above the line (do next)

1. **Startup ffmpeg check (~15 lines).** `shutil.which("ffmpeg")` at boot; if
   missing, render a banner in `index.html` warning that merging/MP3 needs
   ffmpeg, with a download link. Addresses the most likely real-world failure
   (KNOWN_FAILURES #1). Test: monkeypatch `shutil.which`, assert banner flag
   in `/` response.
2. **Surface yt-dlp errors more helpfully.** Map the 3–4 most common error
   strings ("Unsupported URL", "Requested format is not available", DRM) to
   short bilingual messages; show raw text in a collapsible details block.
   Test: error-path unit tests over `download_video` with stubbed YoutubeDL.
3. **Frontend: treat prolonged `unknown` as failure.** After ~15 polls of
   `unknown`, stop and show "job not found — was the app restarted?"
   (KNOWN_FAILURES #2). Pure `index.html` change.
4. **Live-fixture refresh script.** `benchmarks/refresh_fixtures.py` that (on
   a network-enabled machine) runs `yt-dlp -J` on a few public URLs and
   rewrites `fixtures.py` catalogs. Closes the fixtures-drift risk
   (KNOWN_FAILURES #5) without putting network in CI.
5. **Exercise the release workflow once** (push tag `v1.0.0`, download the
   exe, run it on Windows). Until then the exe path is unverified
   (KNOWN_FAILURES #6).

## Below the line (explicitly deferred)

- **Download queue / concurrency cap** — one user, one form, button disables
  while running. Do it when playlists land.
- **SSE instead of polling** — 1 req/s local traffic; no measurable benefit.
- **Vendored CSS replacing Tailwind CDN** — do it only if offline use becomes
  a goal; hand-write ~100 lines rather than vendoring Tailwind.
- **Locking PROGRESS** — replace sweep `del` with `.pop(job_id, None)`
  opportunistically during any future `main.py` edit; a dedicated PR isn't
  warranted.
- **Playlist support, download history, cookies-for-membership-content** —
  real features, need product direction first.
- **Type checking (mypy)** — 320 annotated-free lines; pyflakes + tests cover
  the failure classes seen so far. Reconsider if the codebase grows beyond a
  few files.

## Standing policy

Any PR claiming performance or reliability improvement must include a
measurement (see docs/evaluation-methodology.md). CI enforces: pyflakes,
68-test suite, format benchmark exit code 0.
