"""
OpenRouter integration for contextual, user-facing prompt generation.
Using `arcee-ai/trinity-large-preview:free` model as requested.
"""
from __future__ import annotations
import json
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

async def generate_security_alert(
    amount: float,
    triggers: list[str],
    tx_risk_level: str,
    tx_risk_explanation: str
) -> str:
    """
    Generates a friendly, customer-facing explanation of WHY their transaction
    was held for biometric review, using Arcee Trinity via OpenRouter.
    """
    if not settings.OPENROUTER_API_KEY:
        return "For your security, please verify your identity to complete this high-risk transaction."

    prompt = f"""
    You are a friendly but professional banking security assistant.
    A user just tried to send an unusual transaction that our fraud engine flagged and paused.
    
    Details:
    - Amount: ${amount:,.2f}
    - Risk Level: {tx_risk_level}
    - Internal Fraud Engine Reason: {tx_risk_explanation}
    - Alert Triggers: {", ".join(triggers) if triggers else "General Anomaly"}
    
    Write EXACTLY ONE short, friendly sentence (maximum 20 words) explaining to the user why we paused it, and asking them to complete a quick biometric face scan to unlock the funds. 
    Use a warm, protective tone. Do not include quotes or any standard AI greetings like 'Here is your sentence'.
    """

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hackhers.demo",
        "X-Title": "DeepfakeGate"
    }

    payload = {
        "model": "arcee-ai/trinity-large-preview:free",
        "messages": [
            {"role": "user", "content": prompt.strip()}
        ],
        "temperature": 0.7,
        "max_tokens": 60
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0]["message"]["content"].strip()
            # Trim quotes if generated
            if message.startswith('"') and message.endswith('"'):
                message = message[1:-1]
            return message
    except Exception as exc:
        logger.error("OpenRouter alert generation failed: %s", exc)
        return "For your security, please complete a face scan to authorize this unusual transaction."

async def analyze_frame_for_spoofing(live_b64: str, reference_b64: str | None = None) -> dict:
    """
    Sends a base64 encoded frame (and optionally a reference photo) to Qwen-VL via OpenRouter 
    to detect physical spoofing attacks and optionally perform 1:1 face matching.
    """
    if not settings.OPENROUTER_API_KEY:
        return {"spoof_confidence": 0.0, "vision_flags": [], "face_match_confidence": 1.0}

    prompt = """
    You are an elite anti-spoofing and facial recognition vision model verifying a face scan from a banking app.
    
    TASK 1: ANTI-SPOOFING
    Look closely at the live camera frame. Verify this is an ACTUAL HUMAN BEING standing in real life in front of a camera, NOT a face being shown through another phone or screen.
    Is the user holding up a physical phone screen, a tablet, or a printed photo?
    Look for:
    1. Screen bezels or device borders visible in the frame.
    2. Moiré patterns (pixel grids from screens).
    3. Flash reflections on a glossy screen.
    4. Hands holding a device.
    
    If it appears to be a real human face captured live by a webcam/phone, spoof_confidence should be 0.0.
    If it is clearly a photo or video being displayed on another screen, spoof_confidence should be high (0.8 - 1.0).
    """

    if reference_b64:
        prompt += """
    TASK 2: FACE MATCHING (1:1 Identity Verification)
    You have been provided with TWO images. The FIRST image is the LIVE CAMERA FRAME. The SECOND image is the STORED REFERENCE PHOTO of the account owner.
    Compare the face in the live frame to the face in the reference photo. 
    CRITICAL: You must EXPLICITLY IGNORE clothing, hats, glasses, or accessories. You are comparing the underlying human facial geometry only (bone structure, eye distance, jawline, nose shape).
    Are these two human beings the EXACT same human being? Look closely at facial structures, eye shape, nose shape, and jawline.
    
    Return strictly JSON in the following format:
    {
        "spoof_confidence": <float 0.0 to 1.0>,
        "is_same_person": true or false,
        "face_match_confidence": <float 0.0 to 1.0>,
        "face_match_reasoning": "brief explanation comparing the facial features",
        "vision_flags": ["list", "of", "flags", "like", "phone_bezel_detected", "different_person_detected"]
    }
    """
    else:
        prompt += """
    Return strictly JSON in the following format:
    {
        "spoof_confidence": <float 0.0 to 1.0>,
        "vision_flags": ["list", "of", "flags", "like", "phone_bezel_detected"]
    }
    """

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hackhers.demo",
        "X-Title": "DeepfakeGate"
    }

    content_array = [
        {"type": "text", "text": prompt.strip()},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{live_b64}"
            }
        }
    ]

    if reference_b64:
        content_array.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{reference_b64}"
            }
        })

    payload = {
        "model": "qwen/qwen3-vl-30b-a3b-thinking",
        "messages": [
            {
                "role": "user",
                "content": content_array
            }
        ],
        "temperature": 0.1,
        "max_tokens": 500,
        "response_format": {"type": "json_object"}
    }
    
    logger.info("Sending frame to Qwen-VL for spoof analysis...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0]["message"]["content"].strip()
            
            # Extract JSON from potential <think> blocks
            start_idx = message.find('{')
            end_idx = message.rfind('}')
            if start_idx != -1 and end_idx != -1:
                message = message[start_idx:end_idx+1]
                
            result = json.loads(message)
            logger.info("Qwen-VL result: %s", result)
            return {
                "spoof_confidence": float(result.get("spoof_confidence", 0.0)),
                "is_same_person": result.get("is_same_person", True),
                "face_match_confidence": float(result.get("face_match_confidence", result.get("confidence", 1.0))),
                "face_match_reasoning": result.get("face_match_reasoning", result.get("reasoning", "")),
                "vision_flags": result.get("vision_flags", [])
            }
    except Exception as exc:
        logger.error("Qwen-VL spoof analysis failed: %s", exc)
        return {"spoof_confidence": 0.0, "is_same_person": True, "face_match_confidence": 1.0, "face_match_reasoning": "", "vision_flags": []}

async def evaluate_risk_fallback(system_prompt: str, user_msg: str) -> str:
    """
    If the primary Gemini API SDK fails (e.g. rate limits), this falls back to 
    a free-tier reasoning model on OpenRouter to evaluate the JSON risk payload.
    """
    if not settings.OPENROUTER_API_KEY:
        raise Exception("No OPENROUTER_API_KEY for fallback")

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hackhers.demo",
        "X-Title": "DeepfakeGate"
    }

    payload = {
        "model": "google/gemini-2.0-pro-exp-0205:free",
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_msg.strip()}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    logger.info("Sending risk evaluation to OpenRouter Fallback Model...")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        message = data["choices"][0]["message"]["content"].strip()
        
        start_idx = message.find('{')
        end_idx = message.rfind('}')
        if start_idx != -1 and end_idx != -1:
            message = message[start_idx:end_idx+1]
            
        return message
