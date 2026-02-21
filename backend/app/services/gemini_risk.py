"""
Gemini risk service.
- If GEMINI_API_KEY present: calls Gemini 1.5 Flash with structured prompt.
- If missing: applies deterministic policy rules.
"""
from __future__ import annotations
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """
You are a financial fraud / deepfake risk analyser.
You MUST respond with ONLY valid JSON — no markdown, no extra text.
The response schema is:
{
  "risk_level": "LOW|MEDIUM|HIGH",
  "action": "PASS|RETRY|FAIL|MANUAL_REVIEW",
  "confidence": <0.0-1.0>,
  "reasons": ["string", ...]
}
Use only the fields provided in the user message as evidence.
""".strip()


async def evaluate_risk(
    *,
    scores: dict,                  # deepfake_mean, deepfake_var, liveness, quality, presage
    signals: list[str],
    financial_features: dict,      # avg_amount_30d, max_amount_30d, ...
    transfer: dict,                # amount, rail, ...
    triggers: list[str],
    retry_count: int = 0,
) -> dict:
    """
    Returns:
        {
            "action": "PASS|RETRY|FAIL|MANUAL_REVIEW",
            "risk_level": "LOW|MEDIUM|HIGH",
            "confidence": float,
            "reasons": [str, ...]
        }
    """
    if settings.gemini_configured:
        return await _gemini_evaluate(scores, signals, financial_features, transfer, triggers)
    return _deterministic(scores, financial_features, transfer, triggers, retry_count)


# ---------------------------------------------------------------------------
# Deterministic policy (no API key)
# ---------------------------------------------------------------------------
def _deterministic(
    scores: dict,
    financial_features: dict,
    transfer: dict,
    triggers: list[str],
    retry_count: int,
) -> dict:
    df_mean = scores.get("deepfake_mean", 0.0)
    liveness = scores.get("liveness", 1.0)
    quality = scores.get("quality", 1.0)
    presage = scores.get("presage", 1.0)
    amount = transfer.get("amount", 0.0)
    avg_30d = financial_features.get("avg_amount_30d", 0.0)
    new_device = "new_device" in triggers
    velocity = "high_velocity" in triggers
    reasons: list[str] = []

    if df_mean >= 0.7:
        reasons.append(f"High deepfake score: {df_mean:.2f}")
        return _make(action="FAIL", risk_level="HIGH", confidence=0.95, reasons=reasons)

    low_bio = presage < 0.4 or liveness < 0.4 or quality < 0.4
    if low_bio:
        reasons.extend([
            f"Low bio scores — presage={presage:.2f}, liveness={liveness:.2f}, quality={quality:.2f}"
        ])
        action = "RETRY" if retry_count == 0 else "MANUAL_REVIEW"
        return _make(action=action, risk_level="HIGH", confidence=0.85, reasons=reasons)

    large_tx = avg_30d > 0 and amount > 3 * avg_30d
    if large_tx and new_device:
        reasons.append(f"Amount {amount} >> 3×avg({avg_30d:.2f}) + new device")
        return _make(action="MANUAL_REVIEW", risk_level="HIGH", confidence=0.80, reasons=reasons)

    if velocity and df_mean >= 0.5:
        reasons.append(f"Velocity trigger + elevated deepfake={df_mean:.2f}")
        return _make(action="MANUAL_REVIEW", risk_level="MEDIUM", confidence=0.75, reasons=reasons)

    reasons.append("All bio signals within acceptable range")
    return _make(action="PASS", risk_level="LOW", confidence=0.90, reasons=reasons)


def _make(action: str, risk_level: str, confidence: float, reasons: list[str]) -> dict:
    return {"action": action, "risk_level": risk_level, "confidence": confidence, "reasons": reasons}


# ---------------------------------------------------------------------------
# Gemini live call
# ---------------------------------------------------------------------------
async def _gemini_evaluate(
    scores: dict, signals: list, financial_features: dict, transfer: dict, triggers: list
) -> dict:
    import json
    import google.generativeai as genai      # type: ignore

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"},
    )

    user_msg = json.dumps({
        "scores": scores,
        "signals": signals,
        "financial_features": financial_features,
        "transfer_amount": transfer.get("amount"),
        "rail": transfer.get("rail"),
        "triggers": triggers,
    }, indent=2)

    resp = model.generate_content(user_msg)
    text = resp.text.strip()
    try:
        data = json.loads(text)
        # normalise
        return {
            "action": data.get("action", "MANUAL_REVIEW"),
            "risk_level": data.get("risk_level", "HIGH"),
            "confidence": float(data.get("confidence", 0.5)),
            "reasons": data.get("reasons", []),
        }
    except Exception as exc:
        logger.error("Gemini parse error: %s — raw: %s", exc, text[:200])
        return _make("MANUAL_REVIEW", "HIGH", 0.5, ["Gemini parse error"])


# ---------------------------------------------------------------------------
# Initial risk assessment (pre-video, before challenge)
# ---------------------------------------------------------------------------
def initial_risk_triggers(
    *,
    amount: float,
    new_payee: bool,
    new_device: bool,
    velocity_count: int,
    ip: str | None,
    settings_ref=None,
) -> list[str]:
    s = settings_ref or settings
    triggers: list[str] = []
    if amount >= s.RISK_AMOUNT_THRESHOLD:
        triggers.append(f"high_amount:{amount}")
    if new_payee:
        triggers.append("new_payee")
    if new_device:
        triggers.append("new_device")
    if velocity_count > s.RISK_VELOCITY_MAX:
        triggers.append("high_velocity")
    if ip:
        # simple geo bucketing heuristic: just flag non-RFC-1918 IPs as "external"
        octets = ip.split(".")
        if len(octets) == 4:
            first = int(octets[0]) if octets[0].isdigit() else 0
            if first not in (10, 172, 192, 127):
                triggers.append("external_ip")
    return triggers
