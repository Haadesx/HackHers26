"""
POST /liveness/upload?challenge_id=<id>
multipart/form-data field: video
"""
from __future__ import annotations
import json
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import hash_scores
from app.db import repo
from app.ml.infer import analyze_video_bytes
from app.services import gemini_risk
from app.services import presage_service
from app.services import gateway_fiserv as bank_gw
from app.services import solana_service as sol_gw

router = APIRouter()
logger = get_logger(__name__)


@router.post("/liveness/upload")
async def liveness_upload(
    challenge_id: str = Query(...),
    video: UploadFile = File(...),
    session: AsyncSession = Depends(repo.get_session),
):
    # 1. Load challenge from fast store
    ch_data = await repo.get_challenge(challenge_id)
    if not ch_data:
        raise HTTPException(status_code=404, detail="Challenge not found or expired")

    # 2. Expiry check
    expires_at = datetime.fromisoformat(ch_data["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=410, detail="Challenge expired")

    payment_id = ch_data["payment_id"]
    rail = ch_data["rail"]
    triggers = ch_data["triggers"]
    fin_features = ch_data["financial_features"]
    retry_count = ch_data.get("retry_count", 0)
    solana_pending_id = ch_data.get("solana_pending_id")

    # 3. Read video bytes
    video_bytes = await video.read()
    logger.info("liveness_upload challenge=%s bytes=%d", challenge_id, len(video_bytes))

    # 4. ML inference or DEMO OVERRIDES
    amount = ch_data.get("amount", 0.0)
    amount_str = f"{amount:.2f}"

    if amount_str.endswith(".99"):
        logger.info("DEMO OVERRIDE: Forcing Deepfake FAIL scores for amount %s", amount_str)
        ml_result = {
            "deepfake_mean": 0.88,
            "deepfake_var": 0.15,
            "liveness": 0.85,
            "quality": 0.80,
            "presage": 0.80,
            "signals": ["using_fake_model", "known_deepfake_signature", "high_temporal_inconsistency"],
            "presage_raw": {"micro_motion": 0.8, "smoothness": 0.2, "periodicity_proxy": 0.1, "face_presence_ratio": 1.0}
        }
    elif amount_str.endswith(".98"):
        logger.info("DEMO OVERRIDE: Forcing Poor Lighting RETRY scores for amount %s", amount_str)
        ml_result = {
            "deepfake_mean": 0.05,
            "deepfake_var": 0.01,
            "liveness": 0.30,
            "quality": 0.20,
            "presage": 0.15,
            "signals": ["low_micro_motion", "poor_lighting", "face_obscured"],
            "presage_raw": {"micro_motion": 0.1, "smoothness": 0.8, "periodicity_proxy": 0.0, "face_presence_ratio": 0.5}
        }
    elif amount_str.endswith(".97"):
        logger.info("DEMO OVERRIDE: Forcing Printed Photo SPOOF FAIL scores for amount %s", amount_str)
        ml_result = {
            "deepfake_mean": 0.05,        # Not a deepfake, just a photo
            "deepfake_var": 0.01,
            "liveness": 0.10,             # No life
            "quality": 0.85,              # Good quality photo
            "presage": 0.05,              # Zero micro-motion
            "signals": ["no_micro_motion_detected", "static_image_suspected", "physical_spoof_attempt"],
            "presage_raw": {"micro_motion": 0.0, "smoothness": 1.0, "periodicity_proxy": 0.0, "face_presence_ratio": 1.0}
        }
    else:
        # Normal ML inference — run ML + Presage rPPG + Qwen-VL concurrently for speed
        from app.ml.infer import extract_middle_frame_base64
        from app.services.openrouter_service import analyze_frame_for_spoofing
        import os
        import base64

        # Look for a reference profile photo for 1:1 Face Matching
        user_id = ch_data.get("user_id", "demo_user")
        ref_b64 = None
        profile_path = f"app/static/profiles/{user_id}.jpg"
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "rb") as f:
                    ref_b64 = base64.b64encode(f.read()).decode('utf-8')
                logger.info("Found reference profile photo for user: %s", user_id)
            except Exception as e:
                logger.warning("Failed to load reference photo for %s: %s", user_id, e)

        async def qwen_task():
            b64 = await asyncio.to_thread(extract_middle_frame_base64, video_bytes)
            if b64:
                return await analyze_frame_for_spoofing(b64, reference_b64=ref_b64)
            return {"spoof_confidence": 0.0, "is_same_person": True, "face_match_confidence": 1.0, "face_match_reasoning": "", "vision_flags": []}

        ml_result, presage_result, qwen_result = await asyncio.gather(
            asyncio.to_thread(analyze_video_bytes, video_bytes),
            presage_service.analyze_liveness(video_bytes),
            qwen_task()
        )
        # Merge Presage score into ml_result
        ml_result["presage"] = presage_result["presage_score"]
        if presage_result["spoofing_flags"]:
            ml_result["signals"].extend(presage_result["spoofing_flags"])
            
        # Merge Qwen-VL Face Match and Spoof scores into ml_result
        ml_result["qwen_spoof_confidence"] = qwen_result["spoof_confidence"]
        ml_result["is_same_person"] = qwen_result.get("is_same_person", True)
        ml_result["face_match_confidence"] = qwen_result.get("face_match_confidence", 1.0)
        ml_result["face_match_reasoning"] = qwen_result.get("face_match_reasoning", "")
        if qwen_result["vision_flags"]:
            ml_result["signals"].extend(qwen_result["vision_flags"])

        logger.info(
            "Presage rPPG: mode=%s score=%.3f pulse=%s hr=%s bpm",
            presage_result["mode"],
            presage_result["presage_score"],
            presage_result["pulse_detected"],
            presage_result["heart_rate_bpm"],
        )

    scores = {
        "deepfake_mean": ml_result["deepfake_mean"],
        "deepfake_var": ml_result["deepfake_var"],
        "liveness": ml_result["liveness"],
        "quality": ml_result["quality"],
        "presage": ml_result["presage"],
        "qwen_spoof_confidence": ml_result.get("qwen_spoof_confidence", 0.0),
        "is_same_person": ml_result.get("is_same_person", True),
        "face_match_confidence": ml_result.get("face_match_confidence", 1.0),
        "face_match_reasoning": ml_result.get("face_match_reasoning", ""),
    }
    signals = ml_result.get("signals", [])

    # 5. Fetch transfer for amount info
    transfer = await repo.get_transfer(session, payment_id)
    transfer_info = {
        "amount": transfer.amount if transfer else 0,
        "rail": rail,
    }

    # 6. Gemini risk evaluation
    risk_result = await gemini_risk.evaluate_risk(
        scores=scores,
        signals=signals,
        financial_features=fin_features,
        transfer=transfer_info,
        triggers=triggers,
        retry_count=retry_count,
    )
    decision = risk_result["action"]
    reasons = risk_result["reasons"]

    # 7. Act on decision
    solana_tx: str | None = None
    receipt_tx: str | None = None

    if decision == "PASS":
        payment_status = "EXECUTED"
        if rail == "BANK":
            transfer_rec = await repo.get_transfer(session, payment_id)
            bank_id = transfer_rec.provider_ref if transfer_rec else payment_id
            _, pref = await bank_gw.execute(bank_id)
            await repo.update_transfer_status(session, payment_id, "EXECUTED", provider_ref=pref)
        else:
            solana_tx = await sol_gw.execute_pending_transfer(solana_pending_id or "")
            await repo.update_transfer_status(
                session, payment_id, "EXECUTED", provider_ref=solana_tx
            )
        # Register payee so future transactions to the same recipient
        # are recognised as low-risk.
        user_id = ch_data.get("user_id", "")
        if user_id and transfer:
            recipient_key = (
                f"SOLANA:{transfer.recipient_address}" if rail == "SOLANA"
                else f"BANK:{transfer.recipient_id}"
            )
            await repo.add_known_recipient(session, user_id, recipient_key)

        # Anchor receipt
        scores_hash = hash_scores(scores)
        receipt_tx = await sol_gw.anchor_verification_receipt(
            challenge_id, payment_id, decision, scores_hash
        )
        await repo.create_solana_receipt(
            session, challenge_id, payment_id, decision, scores_hash, receipt_tx
        )
        await _mark_challenge_done(session, challenge_id, retry_count, decision, reasons, scores)
        await repo.delete_challenge(challenge_id)

    elif decision == "FAIL":
        payment_status = "BLOCKED"
        if rail == "BANK":
            transfer_rec = await repo.get_transfer(session, payment_id)
            await bank_gw.cancel(transfer_rec.provider_ref or payment_id)
        else:
            solana_tx = await sol_gw.cancel_pending_transfer(solana_pending_id or "")
        await repo.update_transfer_status(session, payment_id, "BLOCKED")
        scores_hash = hash_scores(scores)
        receipt_tx = await sol_gw.anchor_verification_receipt(
            challenge_id, payment_id, decision, scores_hash
        )
        await repo.create_solana_receipt(
            session, challenge_id, payment_id, decision, scores_hash, receipt_tx
        )
        await _mark_challenge_done(session, challenge_id, retry_count, decision, reasons, scores)
        await repo.delete_challenge(challenge_id)

    elif decision == "RETRY" and retry_count < 1:
        payment_status = "RETRY"
        # Update fast store retry_count
        ch_data["retry_count"] = retry_count + 1
        ttl_remaining = max(1, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
        await repo.store_challenge(challenge_id, ch_data, ttl=ttl_remaining)
        await repo.update_transfer_status(session, payment_id, "HELD")

    else:
        # MANUAL_REVIEW or RETRY exhausted
        decision = "MANUAL_REVIEW"
        payment_status = "HELD"
        await repo.update_transfer_status(session, payment_id, "HELD")
        await _mark_challenge_done(session, challenge_id, retry_count, decision, reasons, scores)
        await repo.delete_challenge(challenge_id)

    return {
        "status": "VERIFIED",
        "decision": decision,
        "challenge_id": challenge_id,
        "scores": scores,
        "reasons": reasons,
        "payment_id": payment_id,
        "payment_status": payment_status,
        "rail": rail,
        "solana_tx": solana_tx,
        "verification_receipt_tx": receipt_tx,
    }


@router.post("/liveness/score")
async def liveness_score(video: UploadFile = File(...)):
    """
    Dedicated endpoint for the iOS app embedded backend.
    Runs ML + Presage + Qwen-VL concurrently and returns the raw scoring JSON.
    """
    video_bytes = await video.read()
    
    from app.ml.infer import extract_middle_frame_base64
    from app.services.openrouter_service import analyze_frame_for_spoofing
    
    async def qwen_task():
        b64 = await asyncio.to_thread(extract_middle_frame_base64, video_bytes)
        if b64:
            return await analyze_frame_for_spoofing(b64)
        return {"spoof_confidence": 0.0, "vision_flags": []}

    ml_result, presage_result, qwen_result = await asyncio.gather(
        asyncio.to_thread(analyze_video_bytes, video_bytes),
        presage_service.analyze_liveness(video_bytes),
        qwen_task()
    )
    
    # Merge Presage score
    ml_result["presage"] = presage_result["presage_score"]
    if presage_result["spoofing_flags"]:
        ml_result["signals"].extend(presage_result["spoofing_flags"])
            
    # Merge Qwen-VL score
    ml_result["qwen_spoof_confidence"] = qwen_result["spoof_confidence"]
    if qwen_result["vision_flags"]:
        ml_result["signals"].extend(qwen_result["vision_flags"])

    scores = {
        "deepfake_mean": ml_result["deepfake_mean"],
        "deepfake_var": ml_result["deepfake_var"],
        "liveness": ml_result["liveness"],
        "quality": ml_result["quality"],
        "presage": ml_result["presage"],
        "qwen_spoof_confidence": ml_result.get("qwen_spoof_confidence", 0.0),
    }
    signals = ml_result.get("signals", [])
    
    return {
        "scores": scores,
        "signals": signals
    }


async def _mark_challenge_done(
    session, challenge_id: str, retry_count: int,
    decision: str, reasons: list, scores: dict,
) -> None:
    await repo.update_challenge_decision(
        session, challenge_id,
        decision=decision,
        reasons=reasons,
        scores=scores,
        retry_count=retry_count,
        used_at=datetime.now(timezone.utc),
    )
