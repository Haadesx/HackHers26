"""
ElevenLabs TTS service.
- Key present → real MP3 (base64 encoded).
- Missing → stub (empty audio).
Caches by message text (memory LRU).
"""
from __future__ import annotations
import base64
import hashlib
from functools import lru_cache
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

MESSAGES = {
    "PASS": "Verification successful. Your payment has been approved and is being processed.",
    "RETRY": "We could not confirm your identity. Please record a clear 3-second face video and try again.",
    "FAIL": "Verification failed. Your payment has been blocked for security reasons. Please contact support.",
    "MANUAL_REVIEW": "Your payment requires manual review. Our team will contact you within 24 hours.",
    "CHALLENGE_REQUIRED": "Identity verification is required for this transaction. Please record a short video.",
    "APPROVED": "Payment approved. Transfer is being executed.",
}

# In-memory cache: text-hash -> base64 mp3
_cache: dict[str, str] = {}


async def speak(decision: str) -> dict:
    """
    Returns {"type": "base64", "value": "<mp3 base64>"}.
    """
    text = MESSAGES.get(decision, f"Payment status: {decision}.")
    cache_key = hashlib.md5(text.encode()).hexdigest()

    if cache_key in _cache:
        return {"type": "base64", "value": _cache[cache_key]}

    if not settings.elevenlabs_configured:
        stub = _silent_mp3_b64()
        _cache[cache_key] = stub
        return {"type": "base64", "value": stub}

    audio_b64 = await _call_elevenlabs(text)
    _cache[cache_key] = audio_b64
    return {"type": "base64", "value": audio_b64}


async def _call_elevenlabs(text: str) -> str:
    import httpx
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode()


def _silent_mp3_b64() -> str:
    """Minimal valid MP3 frame (silent) — 1-frame stub."""
    # ID3v2 tag + one silent MPEG frame
    silent = bytes([
        0xFF, 0xFB, 0x90, 0x00,  # MPEG1, Layer3, 128kbps, 44.1kHz, stereo
    ] + [0x00] * 413)
    return base64.b64encode(silent).decode()
