"""
Fiserv Payments gateway (optional real implementation).
Falls back to simulator if FISERV_* env vars are absent.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
import app.services.gateway_bank_simulator as _sim

logger = get_logger(__name__)
settings = get_settings()

_USE_SIM = not settings.fiserv_configured


async def initiate_transfer(user_id: str, amount: float, recipient_id: str, note: str) -> str:
    if _USE_SIM:
        return await _sim.initiate_transfer(user_id, amount, recipient_id, note)
    return await _real_initiate(user_id, amount, recipient_id, note)


async def hold(payment_id: str) -> None:
    if _USE_SIM:
        return await _sim.hold(payment_id)
    await _real_hold(payment_id)


async def execute(payment_id: str) -> tuple[str, str | None]:
    if _USE_SIM:
        return await _sim.execute(payment_id)
    return await _real_execute(payment_id)


async def cancel(payment_id: str) -> None:
    if _USE_SIM:
        return await _sim.cancel(payment_id)
    await _real_cancel(payment_id)


# ---------------------------------------------------------------------------
# Real Fiserv stubs (wire up when credentials are present)
# ---------------------------------------------------------------------------
async def _real_initiate(user_id: str, amount: float, recipient_id: str, note: str) -> str:
    """POST /payments to Fiserv API."""
    import httpx
    headers = _fiserv_headers()
    payload = {
        "merchantId": settings.FISERV_MERCHANT_ID,
        "amount": {"total": str(int(amount * 100)), "currency": "USD"},
        "transactionDetails": {"captureFlag": "false", "description": note},
        "paymentSource": {"sourceType": "PaymentCard"},
    }
    async with httpx.AsyncClient(base_url=settings.FISERV_BASE_URL, timeout=10) as client:
        resp = await client.post("/ch/payments/v1/charges", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data.get("ipgTransactionId", "UNKNOWN")


async def _real_hold(payment_id: str) -> None:
    logger.info("[FISERV] hold payment_id=%s (pre-auth retained)", payment_id)


async def _real_execute(payment_id: str) -> tuple[str, str | None]:
    import httpx
    headers = _fiserv_headers()
    async with httpx.AsyncClient(base_url=settings.FISERV_BASE_URL, timeout=10) as client:
        resp = await client.post(
            f"/ch/payments/v1/charges/{payment_id}/capture", headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        return "EXECUTED", data.get("ipgTransactionId")


async def _real_cancel(payment_id: str) -> None:
    import httpx
    headers = _fiserv_headers()
    async with httpx.AsyncClient(base_url=settings.FISERV_BASE_URL, timeout=10) as client:
        await client.post(f"/ch/payments/v1/charges/{payment_id}/void", headers=headers)


def _fiserv_headers() -> dict:
    import base64
    credentials = base64.b64encode(
        f"{settings.FISERV_CLIENT_ID}:{settings.FISERV_CLIENT_SECRET}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Identity verification (Fiserv / fallback)
# ---------------------------------------------------------------------------
async def verify_identity_stub(user_id: str) -> dict:
    """Returns a canned identity status for MANUAL_REVIEW fallback."""
    return {
        "user_id": user_id,
        "identity_status": "UNVERIFIED_MANUAL",
        "note": "Full KYC not implemented in MVP; manual review required.",
    }
