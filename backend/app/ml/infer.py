"""
ML inference placeholder — Agent 2 will provide the real implementation.
This stub returns deterministic plausible scores so the backend can run
end-to-end without Agent 2's code.
"""
from __future__ import annotations


async def analyze_video_bytes(video_bytes: bytes) -> dict:
    """
    Agent 2 interface.

    Returns:
    {
        "deepfake_mean": float,   # 0.0 (real) — 1.0 (fake)
        "deepfake_var": float,
        "liveness": float,        # 0.0 (not live) — 1.0 (live)
        "quality": float,         # 0.0 (bad) — 1.0 (good)
        "presage": float,         # 0.0 — 1.0  (Presage Human Sensing)
        "signals": [str, ...],
        "presage_raw": dict       # optional; pass-through
    }
    """
    # Stub: deterministic scores based on video length (byte count heuristic)
    size = len(video_bytes)
    # Larger clips = "better quality" in stub world
    quality = min(1.0, size / 500_000)
    deepfake_mean = 0.10 if size > 50_000 else 0.55
    return {
        "deepfake_mean": round(deepfake_mean, 3),
        "deepfake_var": 0.02,
        "liveness": round(min(1.0, 0.80 + quality * 0.18), 3),
        "quality": round(quality, 3),
        "presage": round(min(1.0, 0.75 + quality * 0.20), 3),
        "signals": ["stub_mode", f"bytes={size}"],
        "presage_raw": {},
    }
