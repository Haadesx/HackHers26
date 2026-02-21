"""SQLAlchemy async models for the audit database."""
from __future__ import annotations
import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    rail = Column(String, nullable=False)        # BANK | SOLANA
    amount = Column(Float, nullable=False)
    recipient_id = Column(String, nullable=True)
    recipient_address = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="INITIATED")  # INITIATED|HELD|EXECUTED|BLOCKED|RETRY
    provider_ref = Column(String, nullable=True)   # bank tx ref or solana tx
    solana_pending_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(String, primary_key=True)
    transfer_id = Column(String, ForeignKey("transfers.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    rail = Column(String, nullable=False)
    triggers_json = Column(Text, default="[]")      # JSON list
    financial_features_json = Column(Text, default="{}")
    scores_json = Column(Text, nullable=True)
    decision = Column(String, nullable=True)
    reasons_json = Column(Text, default="[]")
    retry_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)

    @property
    def triggers(self) -> list:
        return json.loads(self.triggers_json or "[]")

    @property
    def financial_features(self) -> dict:
        return json.loads(self.financial_features_json or "{}")


class KnownRecipient(Base):
    __tablename__ = "known_recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    recipient_key = Column(String, nullable=False)   # "BANK:<id>" or "SOLANA:<addr>"
    created_at = Column(DateTime, default=_now)


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    device_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=_now)


class SolanaReceipt(Base):
    __tablename__ = "solana_receipts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    challenge_id = Column(String, ForeignKey("challenges.id"), nullable=False)
    payment_id = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    scores_hash = Column(String, nullable=False)
    tx_sig = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)
