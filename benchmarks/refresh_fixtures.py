"""Refresh benchmark fixtures from real videos (needs network).

Run this on a machine with YouTube access to keep the synthetic catalogs in
`fixtures.py` honest. It extracts real format lists with yt-dlp (metadata
only, nothing downloaded), strips them to the fields format selection uses,
and writes `fixtures_live.json`. When that file exists, the benchmark and
the parametrized tests automatically include its catalogs alongside the
synthetic ones.

Usage:
    python benchmarks/refresh_fixtures.py [URL ...]
        # default URLs: a couple of stable public videos

The JSON file is intentionally gitignored-by-default-policy-free: commit it
if you want CI to cover real catalogs, or keep it local.
"""
import json
import os
import sys

import yt_dlp

DEFAULT_URLS = [
    # Stable, public, non-age-restricted videos
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # "Me at the zoo"
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
]

KEEP_KEYS = ("format_id", "ext", "vcodec", "acodec", "height", "abr",
             "protocol", "url")

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures_live.json")


def strip_format(f):
    kept = {k: f[k] for k in KEEP_KEYS if f.get(k) is not None}
    # The real URL is irrelevant to selection and may embed tokens: drop it.
    kept["url"] = f"https://example.invalid/{kept.get('format_id', 'x')}"
    return kept


def main(urls):
    catalogs = {}
    ydl = yt_dlp.YoutubeDL({"quiet": True, "skip_download": True})
    for url in urls:
        info = ydl.extract_info(url, download=False)
        name = f"live_{info['extractor_key'].lower()}_{info['id']}"
        catalogs[name] = [strip_format(f) for f in info.get("formats", [])
                          if f.get("format_id")]
        print(f"{name}: {len(catalogs[name])} formats")
    with open(OUT_PATH, "w") as fh:
        json.dump(catalogs, fh, indent=1)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT_URLS)
