"""
GET /audit/challenges
GET /audit/challenges/{challenge_id}
"""
from __future__ import annotations
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repo
from app.db.models import Challenge

router = APIRouter()


def _serialize_challenge(c: Challenge) -> dict:
    return {
        "challenge_id": c.id,
        "transfer_id": c.transfer_id,
        "user_id": c.user_id,
        "rail": c.rail,
        "triggers": json.loads(c.triggers_json or "[]"),
        "financial_features": json.loads(c.financial_features_json or "{}"),
        "scores": json.loads(c.scores_json or "null"),
        "decision": c.decision,
        "reasons": json.loads(c.reasons_json or "[]"),
        "retry_count": c.retry_count,
        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        "used_at": c.used_at.isoformat() if c.used_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/audit/challenges")
async def list_challenges(session: AsyncSession = Depends(repo.get_session)):
    challenges = await repo.list_all_challenges(session)
    return {"challenges": [_serialize_challenge(c) for c in challenges]}


@router.get("/audit/challenges/{challenge_id}")
async def get_challenge(challenge_id: str, session: AsyncSession = Depends(repo.get_session)):
    c = await repo.get_challenge_record(session, challenge_id)
    if not c:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return _serialize_challenge(c)
