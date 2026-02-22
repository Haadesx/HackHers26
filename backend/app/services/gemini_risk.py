"""
Gemini risk service.
- If GEMINI_API_KEY present: calls Gemini 1.5 Flash with structured prompt.
- If missing: applies deterministic policy rules.
"""
from __future__ import annotations
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """
You are a security decision engine.

PART 2 — DEEPFAKE / LIVENESS DECISION LOGIC
Perform liveness verification using the provided numerical signals and the transaction context.

Instead of strict static thresholds, you must holistically evaluate the risk based on the transaction amount:

1. FOR SMALL TRANSACTIONS (Under $50):
   - Be highly forgiving of minor webcam anomalies or compression artifacts.
   - Proceed if face is detected and there are no blatant spoofing signals (e.g. Qwen spoof < 0.7).
   - Only FAIL if `deepfake_mean` is extremely high (> 0.6) or `qwen_spoof_confidence` is very high.

2. FOR MEDIUM TRANSACTIONS ($50 - $500):
   - Require standard verification.
   - `quality` should be reasonable, `deepfake_mean` should be relatively low (< 0.4).
   - Any physical spoofing detected by Qwen Vision should result in a FAIL.

3. FOR LARGE TRANSACTIONS (Over $500):
   - Be extremely strict.
   - Require excellent `quality`, high `liveness`, and very low `deepfake_mean` (< 0.15).
   - Any minor anomaly MUST result in a MANUAL_REVIEW or FAIL.

If the user seems to just have a bad webcam (poor lighting/blur) but is otherwise human, and it's their FIRST try (retry_count=0), output "RETRY".
If `face_match_confidence` is provided and is < 0.6, output FAIL immediately with reason 'Face does not match account owner'. Identity verification supersedes all liveness checks.
Otherwise output "PASS" for good humans, and "FAIL" for detected deepfakes/spoofing.

INPUT FORMAT:
{
  "scores": {
    "deepfake_mean": number,
    "deepfake_var": number,
    "liveness": number,
    "quality": number,
    "presage": number,
    "qwen_spoof_confidence": number,
    "face_match_confidence": number
  },
  "transfer_amount": number,
  "retry_count": integer
}

OUTPUT FORMAT (STRICT):
{
  "final_decision": "PASS" | "FAIL" | "RETRY",
  "risk_level": "LOW" | "HIGH" | "CRITICAL",
  "reason": "concise explanation suitable for terminal logging"
}

You must return STRICT JSON only. Do NOT include markdown. Do NOT include commentary outside JSON.
""".strip()

TRANSACTION_SYSTEM_PROMPT = """
You are a financial fraud risk scoring and security decision engine.

PART 1 — FRAUD RISK SCORING
Evaluate transaction fraud risk using the following rules:

RISK SCORING HEURISTICS:
- Amount < 100 → base risk 10
- Amount 100–1000 → base risk 30
- Amount > 1000 → base risk 60
- If prior_interaction is false → add 15
- If transaction_id appears random or high-entropy → add 10
- Cap total at 100.

RISK LEVEL MAPPING:
- 0–29 → LOW
- 30–69 → MEDIUM
- 70–100 → HIGH

INPUT FORMAT:
{
  "transaction_id": string,
  "user_id": string,
  "recipient_id": string,
  "amount": number,
  "prior_interaction": boolean
}

OUTPUT FORMAT (STRICT):
{
  "risk_percentage": integer (0-100),
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "fraud_explanation": "1-2 sentence explanation"
}

You must return STRICT JSON only. Do NOT include markdown. Do NOT include commentary outside JSON.
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
        try:
            return await _gemini_evaluate(scores, signals, financial_features, transfer, triggers, retry_count)
        except Exception as exc:
            logger.error("Gemini evaluation failed, falling back to deterministic: %s", exc)
    return _deterministic(scores, financial_features, transfer, triggers, retry_count)


async def evaluate_transaction_risk(
    *,
    user_id: str,
    recipient_id: str,
    amount: float,
    transaction_id: str,
    new_payee: bool,
) -> dict:
    """
    Evaluates transaction fraud risk using strictly the financial/historical prompt.
    Returns:
        {
            "risk_percentage": int,
            "risk_level": "LOW|MEDIUM|HIGH",
            "explanation": str
        }
    """
    if not settings.gemini_configured:
        return {"risk_percentage": 0, "risk_level": "LOW", "explanation": "Gemini not configured"}

    import json
    import google.generativeai as genai      # type: ignore

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=TRANSACTION_SYSTEM_PROMPT,
            generation_config={"response_mime_type": "application/json"},
        )

        user_msg = json.dumps({
            "transaction_id": transaction_id,
            "user_id": user_id,
            "recipient_id": recipient_id,
            "amount": amount,
            "prior_interaction": not new_payee
        }, indent=2)

        resp = model.generate_content(user_msg)
        text = resp.text.strip()
        
        logger.info(f"--- GEMINI TRANSACTION SCORING LOGS ---")
        logger.info(f"PAYLOAD SENT: {user_msg}")
        logger.info(f"RAW LLM RESPONSE: {text}")
        logger.info(f"---------------------------------------")

        data = json.loads(text)
        return {
            "risk_percentage": int(data.get("risk_percentage", 50)),
            "risk_level": str(data.get("risk_level", "MEDIUM")),
            "explanation": str(data.get("fraud_explanation", data.get("explanation", ""))),
        }
    except Exception as exc:
        logger.error("Gemini transaction risk eval failed: %s", exc)
        try:
            from app.services.openrouter_service import evaluate_risk_fallback
            logger.info("Triggering OpenRouter Fallback for Transaction Eval")
            fallback_text = await evaluate_risk_fallback(TRANSACTION_SYSTEM_PROMPT, user_msg)
            data = json.loads(fallback_text)
            return {
                "risk_percentage": int(data.get("risk_percentage", 50)),
                "risk_level": str(data.get("risk_level", "MEDIUM")),
                "explanation": str(data.get("fraud_explanation", data.get("explanation", ""))),
            }
        except Exception as fallback_exc:
            logger.error("OpenRouter fallback also failed: %s", fallback_exc)
            return {"risk_percentage": 50, "risk_level": "MEDIUM", "explanation": "Eval failed"}

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
    df_var = scores.get("deepfake_var", 0.0)
    liveness = scores.get("liveness", 1.0)
    quality = scores.get("quality", 1.0)
    presage = scores.get("presage", 1.0)
    qwen_spoof = scores.get("qwen_spoof_confidence", 0.0)
    amount = transfer.get("amount", 0.0)
    avg_30d = financial_features.get("avg_amount_30d", 0.0)
    velocity = "high_velocity" in triggers
    reasons: list[str] = []

    # --- FAIL: deepfake detected ---
    if df_mean >= 0.5 or df_var >= 0.05 or qwen_spoof >= 0.5:
        reasons.append(f"High deepfake/spoof score: mean={df_mean:.2f}, var={df_var:.3f}, vision={qwen_spoof:.2f}")
        return _make(action="FAIL", risk_level="CRITICAL", confidence=0.95, reasons=reasons)

    # --- RETRY / MANUAL_REVIEW: physical spoof / poor bio ---
    low_bio = liveness < 0.4 or quality < 0.4 or presage < 0.2
    if low_bio:
        if df_mean >= 0.3:
            reasons.append(f"Poor biometric quality combined with elevated deepfake score ({df_mean:.2f}).")
            return _make(action="MANUAL_REVIEW", risk_level="HIGH", confidence=0.90, reasons=reasons)
        elif retry_count == 0:
            reasons.append("I'm not sure or no clear face detected, please try again.")
            return _make(action="RETRY", risk_level="MEDIUM", confidence=0.80, reasons=reasons)
        else:
            reasons.append("Please contact the bank for robust verification.")
            return _make(action="MANUAL_REVIEW", risk_level="HIGH", confidence=0.90, reasons=reasons)

    # --- MANUAL_REVIEW: high velocity ---
    if velocity:
        reasons.append("High transaction velocity detected")
        if df_mean >= 0.3:
            reasons.append(f"Elevated deepfake score ({df_mean:.2f}) combined with velocity")
        return _make(action="MANUAL_REVIEW", risk_level="HIGH", confidence=0.80, reasons=reasons)

    # --- MANUAL_REVIEW: anomalous amount (only for users WITH history) ---
    if avg_30d > 0 and amount > 5 * avg_30d:
        reasons.append(f"Amount ${amount:.2f} exceeds 5x avg(${avg_30d:.2f})")
        return _make(action="MANUAL_REVIEW", risk_level="MEDIUM", confidence=0.70, reasons=reasons)

    # --- PASS: all signals look good ---
    reasons.append(
        f"Bio OK — deepfake={df_mean:.2f}, liveness={liveness:.2f}, "
        f"quality={quality:.2f}, presage={presage:.2f}"
    )
    return _make(action="PASS", risk_level="LOW", confidence=0.90, reasons=reasons)


def _make(action: str, risk_level: str, confidence: float, reasons: list[str]) -> dict:
    return {"action": action, "risk_level": risk_level, "confidence": confidence, "reasons": reasons}


# ---------------------------------------------------------------------------
# Gemini live call
# ---------------------------------------------------------------------------
async def _gemini_evaluate(
    scores: dict, signals: list, financial_features: dict, transfer: dict, triggers: list, retry_count: int
) -> dict:
    import json
    import google.generativeai as genai      # type: ignore

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"},
    )

    # Add time-of-day context
    now = datetime.now(timezone.utc)
    user_msg = json.dumps({
        "scores": scores,
        "signals": signals,
        "financial_features": financial_features,
        "transfer_amount": transfer.get("amount"),
        "rail": transfer.get("rail"),
        "triggers": triggers,
        "local_hour": now.hour,
        "is_weekend": now.weekday() >= 5,
        "retry_count": retry_count,
    }, indent=2)

    try:
        resp = model.generate_content(user_msg)
        text = resp.text.strip()
        
        logger.info(f"--- GEMINI LIVENESS RISK LOGS ---")
        logger.info(f"PAYLOAD SENT: {user_msg}")
        logger.info(f"RAW LLM RESPONSE: {text}")
        logger.info(f"---------------------------------")
        data = json.loads(text)
        return {
            "action": data.get("final_decision", data.get("action", "MANUAL_REVIEW")),
            "risk_level": data.get("risk_level", "HIGH"),
            "confidence": float(data.get("confidence", 0.5)),
            "reasons": [data.get("reason", "No reason provided")] if "reason" in data else data.get("reasons", ["No specific reason"]),
        }
    except Exception as exc:
        logger.error("Gemini liveness eval failed: %s", exc)
        try:
            from app.services.openrouter_service import evaluate_risk_fallback
            logger.info("Triggering OpenRouter Fallback for Liveness Eval")
            text = await evaluate_risk_fallback(SYSTEM_PROMPT, user_msg)
            data = json.loads(text)
            return {
                "action": data.get("final_decision", data.get("action", "MANUAL_REVIEW")),
                "risk_level": data.get("risk_level", "HIGH"),
                "confidence": float(data.get("confidence", 0.5)),
                "reasons": [data.get("reason", "No reason provided")] if "reason" in data else data.get("reasons", ["No specific reason"]),
            }
        except Exception as fallback_exc:
            logger.error("OpenRouter fallback parse error: %s — raw: %s", fallback_exc, text[:200] if 'text' in locals() else 'None')
            # Reraise to let evaluate_risk drop into `_deterministic`
            raise fallback_exc


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
        octets = ip.split(".")
        if len(octets) == 4:
            first = int(octets[0]) if octets[0].isdigit() else 0
            if first not in (10, 172, 192, 127):
                triggers.append("external_ip")
    return triggers
