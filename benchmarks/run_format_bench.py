"""Offline benchmark: does each UI choice select a usable format?

For every (file_format, quality) combination the web UI offers, evaluate the
format selector main.py produces against each synthetic catalog using
yt-dlp's real format-selection engine (no network). A cell passes if a
format is selected; it fails if yt-dlp raises "Requested format is not
available" — which surfaces to the user as a failed download.

Usage:
    python benchmarks/run_format_bench.py            # bench current main.py
    python benchmarks/run_format_bench.py --markdown # emit a markdown table

Exit code is the number of failing combinations, so CI can assert 0.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yt_dlp  # noqa: E402
from yt_dlp.utils import YoutubeDLError  # noqa: E402

from benchmarks.fixtures import CATALOGS  # noqa: E402
import main as app_main  # noqa: E402

QUALITIES = ["best", "480p", "720p", "1080p"]
FILE_FORMATS = ["default", "mp4", "webm", "mkv"]


def select(fmt_string, formats):
    """Run yt-dlp's format selection offline. Returns chosen ids or None."""
    ydl = yt_dlp.YoutubeDL(
        {"format": fmt_string, "quiet": True, "simulate": True, "no_warnings": True}
    )
    info = {
        "id": "bench",
        "title": "bench",
        "formats": [dict(f) for f in formats],
        "extractor": "generic",
        "extractor_key": "Generic",
        "webpage_url": "https://example.invalid/watch",
    }
    try:
        result = ydl.process_ie_result(info, download=False)
    except YoutubeDLError:
        return None
    requested = result.get("requested_formats")
    if requested:
        return "+".join(f["format_id"] for f in requested)
    return result.get("format_id")


def run(markdown=False):
    failures = 0
    rows = []
    for catalog_name, formats in CATALOGS.items():
        for file_format in FILE_FORMATS:
            for quality in QUALITIES:
                fmt = app_main.get_format_option(quality, False, file_format)
                chosen = select(fmt, formats)
                ok = chosen is not None
                failures += not ok
                rows.append((catalog_name, file_format, quality, fmt, chosen))
    # audio-only path, once per catalog
    for catalog_name, formats in CATALOGS.items():
        fmt = app_main.get_format_option("best", True, "default")
        chosen = select(fmt, formats)
        failures += chosen is None
        rows.append((catalog_name, "audio-only", "-", fmt, chosen))

    if markdown:
        print("| Catalog | File format | Quality | Selector | Result |")
        print("|---|---|---|---|---|")
        for cat, ff, q, fmt, chosen in rows:
            result = f"`{chosen}`" if chosen else "**FAIL**"
            print(f"| {cat} | {ff} | {q} | `{fmt}` | {result} |")
    else:
        for cat, ff, q, fmt, chosen in rows:
            status = "ok  " if chosen else "FAIL"
            print(f"{status} {cat:18} {ff:10} {q:5} {fmt!r:75} -> {chosen}")
    total = len(rows)
    print(f"\n{total - failures}/{total} combinations select a usable format "
          f"({failures} failures)", file=sys.stderr)
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    sys.exit(run(markdown=args.markdown))
