"""
POST /liveness/upload?challenge_id=<id>
multipart/form-data field: video
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import hash_scores
from app.db import repo
from app.ml.infer import analyze_video_bytes
from app.services import gemini_risk, elevenlabs_tts
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

    # 4. ML inference (Agent 2 interface)
    ml_result = await analyze_video_bytes(video_bytes)
    scores = {
        "deepfake_mean": ml_result["deepfake_mean"],
        "deepfake_var": ml_result["deepfake_var"],
        "liveness": ml_result["liveness"],
        "quality": ml_result["quality"],
        "presage": ml_result["presage"],
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

    voice = await elevenlabs_tts.speak(decision)

    return {
        "status": "VERIFIED",
        "decision": decision,
        "scores": scores,
        "reasons": reasons,
        "payment_id": payment_id,
        "payment_status": payment_status,
        "rail": rail,
        "solana_tx": solana_tx,
        "verification_receipt_tx": receipt_tx,
        "voice_audio": voice,
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
