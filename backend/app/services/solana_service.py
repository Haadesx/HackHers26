"""
Solana service.
- SOLANA_RPC_URL present → real memo transactions via solana-py / solders.
- Missing → stub (null signatures, flow intact).

MVP uses "delayed submission" for escrow:
 - create_pending_transfer: stores intent in DB (no on-chain tx).
 - execute_pending_transfer: sends SOL + Memo or just Memo tx.
 - anchor_verification_receipt: sends a Memo tx containing hash metadata.
"""
from __future__ import annotations
import hashlib
import json
import time
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import generate_id

logger = get_logger(__name__)
settings = get_settings()

# In-memory pending transfer registry (keyed by solana_pending_id)
_pending: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def create_pending_transfer(
    user_id: str, amount: float, recipient_address: str, note: str
) -> tuple[str, str | None]:
    """Returns (solana_pending_id, tx_sig_or_None)."""
    pending_id = generate_id("sol_")
    _pending[pending_id] = {
        "user_id": user_id,
        "amount": amount,
        "recipient_address": recipient_address,
        "note": note,
        "created_at": time.time(),
        "status": "PENDING",
    }
    logger.info("[SOLANA] pending transfer created: %s", pending_id)
    if not settings.solana_configured:
        return pending_id, None
    # Option B: send a Memo tx on hold (minimal, not a real SOL transfer)
    memo = f"HOLD|{pending_id}|{user_id}|{amount}"
    sig = await _send_memo(memo)
    return pending_id, sig


async def execute_pending_transfer(pending_id: str) -> str | None:
    """Execute (send SOL) and return tx signature."""
    entry = _pending.get(pending_id)
    if not entry:
        logger.warning("[SOLANA] pending_id not found: %s", pending_id)
        return None
    entry["status"] = "EXECUTED"
    if not settings.solana_configured:
        return None
    memo = f"EXEC|{pending_id}|{entry['recipient_address']}|{entry['amount']}"
    sig = await _send_memo(memo)
    logger.info("[SOLANA] execute pending_id=%s sig=%s", pending_id, sig)
    return sig


async def cancel_pending_transfer(pending_id: str) -> str | None:
    entry = _pending.get(pending_id)
    if not entry:
        return None
    entry["status"] = "CANCELLED"
    if not settings.solana_configured:
        return None
    sig = await _send_memo(f"CANCEL|{pending_id}")
    logger.info("[SOLANA] cancel pending_id=%s sig=%s", pending_id, sig)
    return sig


async def anchor_verification_receipt(
    challenge_id: str, payment_id: str, decision: str, scores_hash: str
) -> str | None:
    """
    Anchors a tamper-evident receipt on Solana as a Memo transaction.
    Only the hash + metadata are stored on-chain — no PII.
    Returns tx signature or None.
    """
    if not settings.solana_configured:
        logger.info("[SOLANA] not configured — receipt not anchored")
        return None

    payload = {
        "app": "deepfake-gate",
        "challenge_id": challenge_id,
        "payment_id": payment_id,
        "decision": decision,
        "scores_hash": scores_hash,
        "ts": int(time.time()),
    }
    # Use short hash of payload as the actual memo
    memo_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]
    memo = f"RECEIPT|{memo_hash}|{decision}"
    sig = await _send_memo(memo)
    logger.info("[SOLANA] anchored receipt challenge=%s sig=%s", challenge_id, sig)
    return sig


# ---------------------------------------------------------------------------
# Internal: send Memo transaction via solana-py
# ---------------------------------------------------------------------------
async def _send_memo(memo_text: str) -> str | None:
    try:
        from solders.keypair import Keypair       # type: ignore
        from solders.pubkey import Pubkey         # type: ignore
        from solders.transaction import Transaction  # type: ignore
        from solders.instruction import Instruction, AccountMeta  # type: ignore
        from solders.hash import Hash             # type: ignore
        from solders.message import Message       # type: ignore
        import solana.rpc.api as rpc_api          # type: ignore
        import base58                             # type: ignore

        # Load payer keypair
        secret_bytes = base58.b58decode(settings.SOLANA_PAYER_KEYPAIR)
        payer = Keypair.from_bytes(secret_bytes)

        # Memo program v1
        MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")

        client = rpc_api.Client(settings.SOLANA_RPC_URL)
        blockhash_resp = client.get_latest_blockhash()
        recent_blockhash = blockhash_resp.value.blockhash

        memo_bytes = memo_text.encode("utf-8")
        ix = Instruction(
            program_id=MEMO_PROGRAM_ID,
            accounts=[AccountMeta(pubkey=payer.pubkey(), is_signer=True, is_writable=False)],
            data=memo_bytes,
        )
        msg = Message.new_with_blockhash(
            [ix], payer.pubkey(), recent_blockhash
        )
        tx = Transaction([payer], msg, recent_blockhash)
        resp = client.send_transaction(tx)
        return str(resp.value)

    except ImportError:
        logger.warning("[SOLANA] solana-py not installed; returning None")
        return None
    except Exception as exc:
        logger.error("[SOLANA] send_memo error: %s", exc)
        return None
