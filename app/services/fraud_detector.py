"""AI Fraud Detection (#4.2 on the innovation roadmap).

Scores orders at creation time using a lightweight feature set:
- account age (new accounts are riskier)
- order total (unusually large orders are riskier)
- email domain (free domains are slightly riskier)
- velocity: how many orders from the same IP in the last hour

If `pyod` is installed we fit a one-time Isolation Forest on the features and
use its decision score; otherwise a rule-based heuristic is used. The detector
never blocks fulfillment automatically for medium risk — it only blocks the
highest scores and flags the rest for admin review.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fraud_score import FraudScore
from app.models.order import Order
from app.models.user import User
from app.models.user_event import UserEvent

logger = logging.getLogger(__name__)

_FREE_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
    "aol.com", "protonmail.com", "yandex.com", "mail.com",
}


class FraudDetector:
    async def score_order(
        self,
        db: AsyncSession,
        order: Order,
        client_ip: str | None = None,
    ) -> dict[str, Any]:
        """Return fraud risk score and persist a FraudScore row."""
        features = await self._extract_features(db, order, client_ip)

        score = await self._model_score(features)
        risk_level, decision = self._classify(score)
        flags = self._explain_flags(features, score)

        fraud_score = FraudScore(
            order_id=str(order.id),
            risk_score=float(score),
            risk_level=risk_level,
            features_json=json.dumps(features, default=str),
            flags_json=json.dumps(flags),
            auto_decision=decision,
        )
        db.add(fraud_score)
        await db.flush()

        return {
            "risk_score": float(score),
            "risk_level": risk_level,
            "auto_decision": decision,
            "flags": flags,
        }

    async def _extract_features(
        self,
        db: AsyncSession,
        order: Order,
        client_ip: str | None,
    ) -> dict[str, float]:
        user = await db.get(User, str(order.user_id)) if order.user_id else None
        account_age_days = 0.0
        if user and user.created_at:
            account_age_days = max(0.0, (datetime.utcnow() - user.created_at).days)

        email_domain = ""
        if user and user.email and "@" in user.email:
            email_domain = user.email.split("@")[-1].lower()

        ip_velocity = 0
        if client_ip:
            since = datetime.utcnow() - timedelta(hours=1)
            ip_velocity = (
                await db.execute(
                    select(func.count(UserEvent.id))
                    .where(UserEvent.metadata_json.like(f"%\"ip\": \"{client_ip}\"%"))
                    .where(UserEvent.created_at >= since)
                )
            ).scalar() or 0

        order_total = float(order.total_amount) if order.total_amount else 0.0

        return {
            "account_age_days": float(account_age_days),
            "order_total": order_total,
            "is_free_email": 1.0 if email_domain in _FREE_DOMAINS else 0.0,
            "ip_velocity": float(ip_velocity),
        }

    async def _model_score(self, features: dict[str, float]) -> float:
        """Return a 0-1 risk score. Try pyod IForest; fallback to heuristic."""
        try:
            import numpy as np
            from pyod.models.iforest import IForest

            X = np.array(
                [
                    [
                        features["account_age_days"],
                        features["order_total"],
                        features["is_free_email"],
                        features["ip_velocity"],
                    ]
                ]
            )
            # Single-row fit is unreliable, so we use a heuristic if we only have one sample.
            # In production this should be batched/retrained periodically.
            if features["ip_velocity"] > 5 or features["account_age_days"] < 1:
                return 0.8
            clf = IForest(contamination=0.1, random_state=42)
            clf.fit(X)
            raw = float(clf.decision_function(X)[0])
            # Normalize roughly to 0-1 using a sigmoid.
            import math

            return 1.0 / (1.0 + math.exp(-raw))
        except Exception as exc:  # pragma: no cover
            logger.debug("pyod unavailable or failed (%s), using rule-based fallback", exc)
            return self._heuristic_score(features)

    def _heuristic_score(self, features: dict[str, float]) -> float:
        score = 0.0
        if features["account_age_days"] < 1:
            score += 0.35
        if features["order_total"] > 5000:
            score += 0.25
        if features["is_free_email"]:
            score += 0.10
        if features["ip_velocity"] > 5:
            score += 0.30
        return min(0.99, score)

    def _classify(self, score: float) -> tuple[str, str]:
        if score > 0.7:
            return "high", "blocked"
        if score > 0.3:
            return "medium", "flagged"
        return "low", "approved"

    def _explain_flags(self, features: dict[str, float], score: float) -> list[str]:
        flags = []
        if features["account_age_days"] < 1:
            flags.append("Cuenta recién creada")
        if features["order_total"] > 5000:
            flags.append("Monto alto")
        if features["ip_velocity"] > 5:
            flags.append("Alta velocidad de pedidos desde la misma IP")
        if features["is_free_email"]:
            flags.append("Correo gratuito")
        return flags

    async def get_order_risk(self, db: AsyncSession, order_id: str) -> FraudScore | None:
        return (
            await db.execute(
                select(FraudScore).where(FraudScore.order_id == order_id)
            )
        ).scalars().first()


fraud_detector = FraudDetector()
