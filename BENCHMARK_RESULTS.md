# Benchmark Results

Baseline: commit `2d6f640` (2026-08-06). Improved: this branch.
Reproduce with the commands in `docs/evaluation-methodology.md`; raw
per-cell tables in `benchmarks/results/`.

## 1. Format selection success (primary quality metric)

Offline evaluation of every UI choice against yt-dlp 2026.07.04's real
selection engine, across 3 representative video-class catalogs
(4 formats × 4 qualities × 3 catalogs + 3 audio-only = 51 cells).

| | Baseline | Improved |
|---|---|---|
| Combinations selecting a usable format | **24/51 (47%)** | **51/51 (100%)** |
| MKV cells | 0/12 | 12/12 |
| MP4 cells | 5/12 | 12/12 |
| WebM cells | 6/12 | 12/12 |
| default cells | 7/12 | 12/12 |
| audio-only | 2/3 | 3/3 |

Every baseline failure surfaces to the user as a failed download
("Requested format is not available"). Regression check: in all 24 cells
where the baseline succeeded, the improved selector picks the same or a
better format (verified cell-by-cell; e.g. `default/best` now picks 1080p
merged instead of 360p progressive, matching yt-dlp's own default).

Output-container correctness additionally improved: baseline never set
`merge_output_format`, so even "successful" mp4/webm picks could produce a
different container after merge; MKV output was impossible. Now enforced.

## 2. Audio-only bandwidth

Baseline never applied its `bestaudio` selector (assignment bug), so
audio-only jobs downloaded video+audio and discarded the video during MP3
extraction. Improved applies `bestaudio/best`. Saving ≈ the video-track
size per audio job (typically 5–20× the audio size). Verified by
inspection + selector tests; not measured end-to-end (needs network).

## 3. Logger memory (50,000 debug lines ≈ one long fragmented download)

| | Baseline | Improved |
|---|---|---|
| Messages retained | 50,000 | 200 |
| Approx. memory held | 6.9 MiB | 29 KiB (~240× less) |

Honest scope: baseline memory was freed when the download thread exited —
transient waste per active download, not a permanent leak.

## 4. Security: cross-site POST to loopback

| Case | Baseline | Improved |
|---|---|---|
| `Origin: https://evil.example` | job started | 403 |
| `Origin: null` | job started | 403 |
| DNS-rebinding (`Host: evil.example`) | job started | 403 |
| Legit browser (local Origin) | 200 | 200 |
| curl/scripts (no Origin) | 200 | 200 |

## 5. Falsified claims from the previous optimization pass (negative results)

| Claim (prior commit) | Measurement | Verdict |
|---|---|---|
| `threaded=True` enables concurrent request handling | Flask ≥1.0 `app.run` defaults `threaded=True` (`options.setdefault`) | **No-op.** Kept as documentation only |
| Hoisting FORMAT_MAP avoids rebuild cost | 0.57 µs → 0.08 µs per call; called once per download | **Negligible.** Readability change mislabeled as optimization; table since deleted anyway |
| TTL sweep prevents memory growth | Correct in intent, but its interaction with timestamp-less error entries deleted fresh user-visible errors | **Introduced a bug**, fixed + regression-tested this pass |

## 6. Test/lint status

Baseline: 0 tests, no linter. Improved: 68 pytest tests (2.4 s, fully
offline) + pyflakes, both green and enforced in CI alongside the benchmark
(CI fails if any format cell regresses).
