"""
POST /payments/initiate — dual-rail payment initiation with risk triggers.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import generate_id
from app.db import repo
from app.services import gemini_risk
from app.services import gateway_fiserv as bank_gw
from app.services import solana_service as sol_gw
from app.services import openrouter_service


router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


class InitiateRequest(BaseModel):
    user_id: str
    rail: str                           # BANK | SOLANA
    amount: float
    recipient_id: str = ""
    recipient_address: str | None = None
    note: str = ""
    device_id: str = ""
    user_agent: str = ""
    ip: str | None = None


@router.post("/payments/initiate")
async def initiate_payment(
    req: InitiateRequest,
    session: AsyncSession = Depends(repo.get_session),
):
    rail = req.rail.upper()
    if rail not in ("BANK", "SOLANA"):
        return {"error": "rail must be BANK or SOLANA"}, 400

    recipient_key = (
        f"SOLANA:{req.recipient_address}" if rail == "SOLANA"
        else f"BANK:{req.recipient_id}"
    )

    # --- Know devices/payees ---
    new_device = not await repo.is_known_device(session, req.user_id, req.device_id)
    new_payee = not await repo.is_known_recipient(session, req.user_id, recipient_key)

    # --- Velocity ---
    velocity_count = await repo.count_recent_initiations(
        session, req.user_id, settings.RISK_VELOCITY_WINDOW_SECONDS
    )

    # --- Financial features (needed for risk evaluation) ---
    fin_features = await repo.get_financial_features(session, req.user_id)

    # --- New Financial Fraud Scoring Engine ---
    tx_risk = await gemini_risk.evaluate_transaction_risk(
        user_id=req.user_id,
        recipient_id=req.recipient_id or str(req.recipient_address),
        amount=req.amount,
        transaction_id=generate_id("tx_"),
        new_payee=new_payee
    )
    
    logger.info("Transaction Risk Engine: %d%% (%s) because: %s", 
                tx_risk.get("risk_percentage", 0), tx_risk.get("risk_level", "MEDIUM"), tx_risk.get("explanation", "missing"))
    
    triggers = []
    if new_device: triggers.append("new_device")
    if velocity_count > settings.RISK_VELOCITY_MAX: triggers.append("high_velocity")
    if tx_risk.get("risk_percentage", 0) >= 60: triggers.append("high_fraud_score")

    # --- Create transfer record ---
    payment_id = generate_id("pay_")
    transfer = await repo.create_transfer(
        session,
        id=payment_id,
        user_id=req.user_id,
        rail=rail,
        amount=req.amount,
        recipient_id=req.recipient_id or None,
        recipient_address=req.recipient_address,
        note=req.note,
        status="INITIATED",
    )

    # High risk = any hard triggers OR Gemini scores transaction risk level as MEDIUM or HIGH
    gemini_risk_level = tx_risk.get("risk_level", "MEDIUM")
    high_risk = len(triggers) > 0 or gemini_risk_level in ["MEDIUM", "HIGH", "CRITICAL"]
    logger.info("high_risk=%s (risk_level=%s triggers=%s)", high_risk, gemini_risk_level, triggers)

    if not high_risk:
        # ---- Low risk: execute immediately ----
        solana_tx = None
        if rail == "BANK":
            bank_id = await bank_gw.initiate_transfer(
                req.user_id, req.amount, req.recipient_id, req.note
            )
            _, provider_ref = await bank_gw.execute(bank_id)
            await repo.update_transfer_status(session, payment_id, "EXECUTED", provider_ref=provider_ref)
        else:
            pending_id, hold_sig = await sol_gw.create_pending_transfer(
                req.user_id, req.amount, req.recipient_address or "", req.note
            )
            solana_tx = await sol_gw.execute_pending_transfer(pending_id)
            await repo.update_transfer_status(
                session, payment_id, "EXECUTED",
                provider_ref=solana_tx, solana_pending_id=pending_id
            )

        # Register device/payee on success
        await repo.add_device(session, req.user_id, req.device_id)
        await repo.add_known_recipient(session, req.user_id, recipient_key)

        return {
            "status": "APPROVED",
            "payment_id": payment_id,
            "payment_status": "EXECUTED",
            "rail": rail,
            "solana_tx": solana_tx,
            "voice_audio": None,
        }

    # ---- High risk: hold + challenge ----
    if rail == "BANK":
        bank_id = await bank_gw.initiate_transfer(
            req.user_id, req.amount, req.recipient_id, req.note
        )
        await bank_gw.hold(bank_id)
        await repo.update_transfer_status(session, payment_id, "HELD", provider_ref=bank_id)
        hold_solana_tx = None
    else:
        pending_id, hold_sig = await sol_gw.create_pending_transfer(
            req.user_id, req.amount, req.recipient_address or "", req.note
        )
        await repo.update_transfer_status(
            session, payment_id, "HELD", solana_pending_id=pending_id
        )
        hold_solana_tx = hold_sig

    challenge_id = generate_id("chg_")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.CHALLENGE_TTL_SECONDS)

    await repo.create_challenge_record(
        session,
        id=challenge_id,
        transfer_id=payment_id,
        user_id=req.user_id,
        rail=rail,
        triggers_json=json.dumps(triggers),
        financial_features_json=json.dumps(fin_features),
        expires_at=expires_at,
    )

    # Store in fast store for liveness upload lookup
    await repo.store_challenge(challenge_id, {
        "payment_id": payment_id,
        "user_id": req.user_id,
        "amount": req.amount,
        "rail": rail,
        "triggers": triggers,
        "financial_features": fin_features,
        "retry_count": 0,
        "expires_at": expires_at.isoformat(),
        "solana_pending_id": pending_id if rail == "SOLANA" else None,
    }, ttl=settings.CHALLENGE_TTL_SECONDS + 30)

    # Generate customer-facing explanation via Arcee Trinity
    security_message = await openrouter_service.generate_security_alert(
        amount=req.amount,
        triggers=triggers,
        tx_risk_level=tx_risk.get("risk_level", "HIGH"),
        tx_risk_explanation=tx_risk.get("explanation", "High transaction risk")
    )

    return {
        "status": "CHALLENGE_REQUIRED",
        "challenge_id": challenge_id,
        "prompt": "Please record a clear 3-second face video for identity verification.",
        "security_message": security_message,
        "expires_at": expires_at.isoformat(),
        "payment_id": payment_id,
        "payment_status": "HELD",
        "rail": rail,
        "solana_tx": hold_solana_tx,
    }
