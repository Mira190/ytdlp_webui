"""Synthetic format catalogs for offline format-selection benchmarking.

Each catalog is a list of format dicts shaped like yt-dlp extractor output.
They model real classes of videos this app's users hit, so a selector that
fails here fails for real users:

- youtube_standard: modern YouTube — video-only H.264/mp4 and VP9/webm
  ladders, audio-only m4a and opus, plus the progressive 360p mp4 (itag 18).
- youtube_no_m4a: same but with no m4a audio track (some videos/livestream
  VODs only expose opus audio).
- progressive_only: sites whose extractors return only muxed
  (video+audio) files — no video-only/audio-only streams to merge.
"""


def _f(fid, ext, vcodec, acodec, height=None, abr=None):
    d = {
        "format_id": fid,
        "ext": ext,
        "vcodec": vcodec,
        "acodec": acodec,
        "url": f"https://example.invalid/{fid}",
        "protocol": "https",
    }
    if height is not None:
        d["height"] = height
    if abr is not None:
        d["abr"] = abr
    return d


youtube_standard = [
    _f("18", "mp4", "avc1.42001E", "mp4a.40.2", height=360),
    _f("135", "mp4", "avc1.4d401f", "none", height=480),
    _f("136", "mp4", "avc1.4d401f", "none", height=720),
    _f("137", "mp4", "avc1.640028", "none", height=1080),
    _f("244", "webm", "vp9", "none", height=480),
    _f("247", "webm", "vp9", "none", height=720),
    _f("248", "webm", "vp9", "none", height=1080),
    _f("140", "m4a", "none", "mp4a.40.2", abr=129),
    _f("251", "webm", "none", "opus", abr=140),
]

youtube_no_m4a = [
    _f("135", "mp4", "avc1.4d401f", "none", height=480),
    _f("136", "mp4", "avc1.4d401f", "none", height=720),
    _f("137", "mp4", "avc1.640028", "none", height=1080),
    _f("248", "webm", "vp9", "none", height=1080),
    _f("251", "webm", "none", "opus", abr=140),
]

progressive_only = [
    _f("sd", "mp4", "avc1.42001E", "mp4a.40.2", height=480),
    _f("hd", "mp4", "avc1.640028", "mp4a.40.2", height=720),
]

CATALOGS = {
    "youtube_standard": youtube_standard,
    "youtube_no_m4a": youtube_no_m4a,
    "progressive_only": progressive_only,
}
