"""Data access / repository layer (async SQLAlchemy + optional Redis)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Base, Transfer, Challenge, KnownRecipient, Device, SolanaReceipt

logger = get_logger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Engine / Session
# ---------------------------------------------------------------------------
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB tables initialised")


async def get_session() -> AsyncSession:      # noqa: D401
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# In-memory challenge store (Redis fallback)
# ---------------------------------------------------------------------------
_challenge_store: dict[str, dict] = {}
_redis_client = None


async def _init_redis() -> None:
    global _redis_client
    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis        # type: ignore
            _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await _redis_client.ping()
            logger.info("Redis connected")
        except Exception as exc:
            logger.warning("Redis unavailable, using in-memory store: %s", exc)
            _redis_client = None


async def store_challenge(challenge_id: str, data: dict, ttl: int) -> None:
    if _redis_client:
        await _redis_client.setex(f"challenge:{challenge_id}", ttl, json.dumps(data))
    else:
        _challenge_store[challenge_id] = data


async def get_challenge(challenge_id: str) -> Optional[dict]:
    if _redis_client:
        raw = await _redis_client.get(f"challenge:{challenge_id}")
        return json.loads(raw) if raw else None
    return _challenge_store.get(challenge_id)


async def delete_challenge(challenge_id: str) -> None:
    if _redis_client:
        await _redis_client.delete(f"challenge:{challenge_id}")
    else:
        _challenge_store.pop(challenge_id, None)


# ---------------------------------------------------------------------------
# Transfer helpers
# ---------------------------------------------------------------------------
async def create_transfer(session: AsyncSession, **kwargs) -> Transfer:
    t = Transfer(**kwargs)
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


async def get_transfer(session: AsyncSession, transfer_id: str) -> Optional[Transfer]:
    result = await session.execute(select(Transfer).where(Transfer.id == transfer_id))
    return result.scalar_one_or_none()


async def update_transfer_status(session: AsyncSession, transfer_id: str, status: str,
                                  provider_ref: str = None, solana_pending_id: str = None) -> None:
    t = await get_transfer(session, transfer_id)
    if t:
        t.status = status
        if provider_ref is not None:
            t.provider_ref = provider_ref
        if solana_pending_id is not None:
            t.solana_pending_id = solana_pending_id
        await session.commit()


# ---------------------------------------------------------------------------
# Challenge helpers
# ---------------------------------------------------------------------------
async def create_challenge_record(session: AsyncSession, **kwargs) -> Challenge:
    c = Challenge(**kwargs)
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


async def get_challenge_record(session: AsyncSession, challenge_id: str) -> Optional[Challenge]:
    result = await session.execute(select(Challenge).where(Challenge.id == challenge_id))
    return result.scalar_one_or_none()


async def update_challenge_decision(session: AsyncSession, challenge_id: str,
                                     decision: str, reasons: list, scores: dict,
                                     retry_count: int, used_at: datetime) -> None:
    c = await get_challenge_record(session, challenge_id)
    if c:
        c.decision = decision
        c.reasons_json = json.dumps(reasons)
        c.scores_json = json.dumps(scores)
        c.retry_count = retry_count
        c.used_at = used_at
        await session.commit()


# ---------------------------------------------------------------------------
# KnownRecipient helpers
# ---------------------------------------------------------------------------
async def is_known_recipient(session: AsyncSession, user_id: str, recipient_key: str) -> bool:
    result = await session.execute(
        select(KnownRecipient).where(
            KnownRecipient.user_id == user_id,
            KnownRecipient.recipient_key == recipient_key,
        )
    )
    return result.scalar_one_or_none() is not None


async def add_known_recipient(session: AsyncSession, user_id: str, recipient_key: str) -> None:
    existing = await is_known_recipient(session, user_id, recipient_key)
    if not existing:
        session.add(KnownRecipient(user_id=user_id, recipient_key=recipient_key))
        await session.commit()


# ---------------------------------------------------------------------------
# Device helpers
# ---------------------------------------------------------------------------
async def is_known_device(session: AsyncSession, user_id: str, device_id: str) -> bool:
    result = await session.execute(
        select(Device).where(Device.user_id == user_id, Device.device_id == device_id)
    )
    return result.scalar_one_or_none() is not None


async def add_device(session: AsyncSession, user_id: str, device_id: str) -> None:
    if not await is_known_device(session, user_id, device_id):
        session.add(Device(user_id=user_id, device_id=device_id))
        await session.commit()


# ---------------------------------------------------------------------------
# Velocity + Financial features
# ---------------------------------------------------------------------------
async def count_recent_initiations(session: AsyncSession, user_id: str, window_seconds: int) -> int:
    since = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    result = await session.execute(
        select(func.count()).where(Transfer.user_id == user_id, Transfer.created_at >= since)
    )
    return result.scalar_one() or 0


async def get_financial_features(session: AsyncSession, user_id: str) -> dict:
    """Compute rolling financial features from transfer history."""
    since_30d = datetime.now(timezone.utc) - timedelta(days=30)
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    result_30d = await session.execute(
        select(Transfer.amount).where(
            Transfer.user_id == user_id,
            Transfer.created_at >= since_30d,
            Transfer.status == "EXECUTED",
        )
    )
    amounts_30d = [r[0] for r in result_30d.fetchall()]

    result_24h = await session.execute(
        select(func.count()).where(
            Transfer.user_id == user_id,
            Transfer.created_at >= since_24h,
        )
    )
    count_24h = result_24h.scalar_one() or 0

    result_recipients = await session.execute(
        select(func.count()).where(KnownRecipient.user_id == user_id)
    )
    known_count = result_recipients.scalar_one() or 0

    result_total = await session.execute(
        select(func.count()).where(Transfer.user_id == user_id, Transfer.status == "EXECUTED")
    )
    total_tx = result_total.scalar_one() or 1  # avoid divide by zero

    avg_30d = sum(amounts_30d) / len(amounts_30d) if amounts_30d else 0.0
    max_30d = max(amounts_30d) if amounts_30d else 0.0

    return {
        "avg_amount_30d": round(avg_30d, 2),
        "max_amount_30d": round(max_30d, 2),
        "transfers_count_24h": count_24h,
        "known_recipient_ratio": round(known_count / total_tx, 3),
    }


# ---------------------------------------------------------------------------
# Solana receipt
# ---------------------------------------------------------------------------
async def create_solana_receipt(session: AsyncSession, challenge_id: str,
                                 payment_id: str, decision: str,
                                 scores_hash: str, tx_sig: Optional[str]) -> SolanaReceipt:
    r = SolanaReceipt(
        challenge_id=challenge_id, payment_id=payment_id,
        decision=decision, scores_hash=scores_hash, tx_sig=tx_sig,
    )
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return r


# ---------------------------------------------------------------------------
# Audit list fetchers
# ---------------------------------------------------------------------------
async def list_all_challenges(session: AsyncSession) -> list[Challenge]:
    result = await session.execute(select(Challenge).order_by(Challenge.created_at.desc()))
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Demo data seeding
# ---------------------------------------------------------------------------
async def seed_demo_data() -> None:
    """Pre-populate the demo_user with realistic transaction history.

    This ensures the first payment from the frontend doesn't get flagged
    simply because there's no prior history. Only seeds if no transfers
    exist yet (i.e. first run).
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count()).where(Transfer.user_id == "demo_user")
        )
        count = result.scalar_one() or 0
        if count > 0:
            return  # already seeded

        logger.info("Seeding demo data for demo_user")

        demo_device_id = "device_demo_default"
        demo_recipient = "BANK:demo_recipient_001"

        # Register a known device
        session.add(Device(user_id="demo_user", device_id=demo_device_id))

        # Register a known recipient
        session.add(KnownRecipient(user_id="demo_user", recipient_key=demo_recipient))

        # Create a few past executed transfers so get_financial_features
        # returns meaningful data (avg ~$200, max ~$500)
        now = datetime.now(timezone.utc)
        seed_transfers = [
            {"amount": 150.00, "days_ago": 25},
            {"amount": 75.50,  "days_ago": 20},
            {"amount": 200.00, "days_ago": 15},
            {"amount": 320.00, "days_ago": 10},
            {"amount": 95.00,  "days_ago": 5},
            {"amount": 500.00, "days_ago": 2},
        ]
        for i, tx in enumerate(seed_transfers):
            t = Transfer(
                id=f"pay_seed_{i:03d}",
                user_id="demo_user",
                rail="BANK",
                amount=tx["amount"],
                recipient_id="demo_recipient_001",
                note="Seed transaction",
                status="EXECUTED",
                created_at=now - timedelta(days=tx["days_ago"]),
            )
            session.add(t)

        await session.commit()
        logger.info("Demo data seeded: %d transfers, 1 device, 1 recipient", len(seed_transfers))
