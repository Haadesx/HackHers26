"""Bank payment gateway simulator — always available, no external keys needed."""
from __future__ import annotations
import asyncio
import random
import string
from app.core.logging import get_logger
from app.core.security import generate_id

logger = get_logger(__name__)

_pending: dict[str, dict] = {}   # payment_id -> state


def _rand_ref() -> str:
    return "SIM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


async def initiate_transfer(user_id: str, amount: float, recipient_id: str, note: str) -> str:
    """Returns payment_id (held internally as INITIATED)."""
    payment_id = generate_id("txn_")
    _pending[payment_id] = {
        "user_id": user_id, "amount": amount,
        "recipient_id": recipient_id, "note": note,
        "status": "INITIATED", "ref": None,
    }
    logger.info("[SIM] initiate_transfer payment_id=%s amount=%.2f", payment_id, amount)
    return payment_id


async def hold(payment_id: str) -> None:
    if payment_id in _pending:
        _pending[payment_id]["status"] = "HELD"
        logger.info("[SIM] hold payment_id=%s", payment_id)


async def execute(payment_id: str) -> tuple[str, str | None]:
    """Returns (status, provider_ref)."""
    await asyncio.sleep(0.05)   # simulate network
    if payment_id not in _pending:
        return "NOT_FOUND", None
    ref = _rand_ref()
    _pending[payment_id]["status"] = "EXECUTED"
    _pending[payment_id]["ref"] = ref
    logger.info("[SIM] execute payment_id=%s ref=%s", payment_id, ref)
    return "EXECUTED", ref


async def cancel(payment_id: str) -> None:
    if payment_id in _pending:
        _pending[payment_id]["status"] = "CANCELLED"
        logger.info("[SIM] cancel payment_id=%s", payment_id)
