# Critical Review (repository-wide, from first principles)

Reviewed at baseline commit `2d6f640` (2026-08-06). Method: reconstruct the
project goal (see architecture.md), then audit every file against it, run the
system, and *measure* suspected defects before ranking them. Findings marked
**FIXED** were implemented in this pass with tests; evidence lives in
BENCHMARK_RESULTS.md and `tests/`.

## Ranked findings

Ranking = expected user value × severity × confidence, discounted by cost.

### 1. Format selection silently broken for most UI choices — **FIXED**
- **Problem:** the 2021-era format table hard-required stream properties many
  videos don't have. MKV used `[ext=mkv]`, which can never match (mkv is a
  merge container; no site serves mkv streams). MP4 quality tiers required an
  m4a track with no fallback. Nothing enforced the output container at all.
- **Evidence:** offline benchmark against yt-dlp's real selection engine:
  **27 of 51** UI combinations raised "Requested format is not available"
  (all 12 MKV cells, MP4 tiers on no-m4a videos, nearly everything on
  progressive-only sites, even `best` on merge-only videos).
- **Layer:** selector construction in `get_format_option` — the only place the
  UI's intent is translated for yt-dlp. Correct layer.
- **Fix (simplest viable):** height-based selectors ending in a
  `bestvideo+bestaudio/best` fallback chain; container preference as the first
  alternative only; `merge_output_format` for mp4/webm/mkv.
- **Result:** 51/51 select a format; preferred picks unchanged where the old
  code worked (verified cell-by-cell).
- **Falsifier:** a catalog where the new chain selects nothing, or picks a
  worse format than the old string did. Neither occurred.

### 2. Cross-site POST to loopback — **FIXED**
- **Problem:** "binds 127.0.0.1 so it's safe" is a false assumption. Simple
  form POSTs are exempt from CORS preflight, so any webpage the user visits
  could trigger downloads of attacker-chosen URLs to attacker-chosen paths
  (`download_dir` is a free-text field and the server creates it).
- **Evidence:** demonstrated pre-fix with a forged `Origin: https://evil.example`
  POST — job accepted (see test suite for the reproduction).
- **Fix:** `before_request` guard: Host and Origin (when present) must be
  loopback names; `Origin: null` blocked; Origin-less non-browser clients
  allowed. 6 policy cases tested.
- **Residual risk:** a hostile *local* process can still POST (no auth); out of
  scope for a single-user machine tool.

### 3. Audio-only downloads fetched full video — **FIXED**
- **Problem:** `get_format_option` returned `bestaudio` for audio-only, but
  `download_video` only assigned `ydl_opts["format"]` in the video branch, so
  audio-only jobs used yt-dlp's default (video+audio), downloading the video
  track just to discard it during MP3 extraction. Also `extractaudio`/
  `audioformat` are CLI-era keys the Python API ignores — dead config.
- **Evidence:** code path inspection; the computed selector was provably
  unused in that branch.
- **Fix:** assign the selector (`bestaudio/best`) in the audio branch; drop the
  dead keys. Bandwidth saving is roughly the video-track size per audio job.

### 4. Fresh error entries swept by TTL cleanup — **FIXED** (self-introduced)
- **Problem:** the TTL sweep added earlier in this branch treats a missing
  `updated_at` as infinitely old; `download_video`'s except-handler wrote error
  entries without one, so the next download start could delete a user's error
  message before they saw it.
- **Evidence/testing:** regression test `test_download_error_survives_cleanup`.
  This is a defect introduced by a previous "optimization" commit and caught by
  this review — see DECISIONS.md on reviewing one's own diffs adversarially.

### 5. Unbounded logger growth during long downloads — **FIXED**
- **Problem:** `SimpleLogger` kept every message; yt-dlp logs per fragment.
- **Evidence:** 50k debug lines retained ≈ 6.9 MiB, read by nobody. Honest
  scope: memory is freed when the download thread exits, so this was transient
  waste per active download, **not** a permanent leak.
- **Fix:** `deque(maxlen=200)` → 29 KiB for the same workload.

### 6. Claims from the previous optimization pass that did not survive scrutiny
- **`threaded=True`:** Flask's `app.run` does `options.setdefault("threaded",
  True)` since 1.0 — the change was a **no-op**. Kept only as documentation of
  intent.
- **FORMAT_MAP hoisting:** measured ~0.5 µs saved on a function called once per
  download — **negligible**; it was a readability change mislabeled as an
  optimization. (The table it hoisted was itself the broken artifact of
  finding #1 and is now deleted.)

## Non-findings (checked, judged acceptable — details in technical-debt.md)
- No lock on `PROGRESS` (GIL-atomic single assignments; snapshot-then-delete sweep).
- Polling instead of SSE (1 req/s for one local user is irrelevant load).
- Tailwind from CDN (offline UI degrades unstyled but functional).
- `download_dir` free-text path (it's the product feature on a local tool, now
  unreachable cross-site).
- No persistence of jobs across restart (single-user tool; restart-and-retry
  is an acceptable recovery story).
