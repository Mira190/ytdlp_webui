# Evaluation Methodology

## Principles

1. **Measure before ranking.** A suspected defect gets a reproduction or a
   number before it gets priority. Two prior "optimizations" died under this
   rule (see DECISIONS.md #5).
2. **Offline and deterministic.** YouTube cannot be fetched from CI, and live
   catalogs drift. All evaluation runs against synthetic fixtures through
   yt-dlp's *real* selection engine, so results are reproducible and fast
   (<3 s), at the cost of one stated gap: end-to-end downloads are unverified
   in CI (KNOWN_FAILURES.md).
3. **Every fix lands with a test that fails on the old code.**

## Instruments

### Format-selection benchmark (`benchmarks/`)
- **Tasks:** the full UI matrix — 4 file formats × 4 qualities + audio-only —
  evaluated against 3 catalogs in `benchmarks/fixtures.py` modeling real
  video classes (modern YouTube, no-m4a YouTube, progressive-only sites).
- **Runner:** `benchmarks/run_format_bench.py` feeds each selector into
  `yt_dlp.YoutubeDL.process_ie_result` with `simulate=True` (no network).
- **Scorer:** a cell passes iff a format is selected; the run's exit code is
  the failure count, so CI asserts zero. Chosen format ids are printed so
  quality regressions (e.g. 1080p cell picking 360p) are visible by diffing
  `benchmarks/results/`.
- **Baseline / improved:** `results/baseline-2d6f640.md` (24/51) vs
  `results/improved.md` (51/51).

### Test suite (`tests/test_app.py`, 68 tests)
Routes, cross-site POST policy (6 cases), progress lifecycle, TTL sweep,
error-survives-cleanup regression, format matrix (parametrized through the
benchmark scorer), container/quality preference pins, logger bound.

### Micro-measurements (recorded in BENCHMARK_RESULTS.md)
`timeit` for the dict-hoisting claim; `sys.getsizeof` sums for logger memory;
live-server smoke test for the origin guard (real HTTP, not just test client).

## How to re-run everything

```bash
pip install -r requirements.txt pytest pyflakes
python -m pyflakes main.py tests benchmarks
python -m pytest tests/ -q
python benchmarks/run_format_bench.py            # exit code = failures
python benchmarks/run_format_bench.py --markdown # table for results/
```

## Adding a new video-class fixture

Add a catalog (list of format dicts) to `CATALOGS` in
`benchmarks/fixtures.py`. The benchmark and the parametrized tests pick it up
automatically. Model it on real `yt-dlp -J <url>` output: `vcodec`/`acodec`
`"none"` markers distinguish video-only/audio-only/muxed streams.

## What would change our conclusions

- A fixture (drawn from a real site) where the fallback chain selects nothing
  → the format fix is incomplete.
- A fixture where the new chain picks a *worse* format than the old table did
  → the fix caused a quality regression.
- A legitimate browser flow that hits the 403 guard → the origin policy is too
  strict (watch for `Origin` values beyond loopback/null in bug reports).
