"""Agentic checkout (#4.1 on the innovation roadmap).

A lightweight state-machine agent that can complete an order via chat. It:
- Detects checkout intent and guides the user through item/address/confirm steps
- Enforces a spending limit and explicit "sí, comprar" confirmation gate
- Persists every action to the `agent_actions` audit log
- Never blocks order fulfillment on scoring side effects
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_action import AgentAction
from app.models.product import Product
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.agents.base import BaseAgent, AgentResult
from app.services.order_service import order_service
from app.services.search_service import search_service


class CheckoutAgent(BaseAgent):
    name = "checkout"
    SPENDING_LIMIT = Decimal("5000")

    def __init__(self):
        # In-memory session state. A production deployment may persist this to
        # Redis/SQLite, but the audit log (`agent_actions`) already provides
        # durability for each transition.
        self._sessions: dict[str, dict[str, Any]] = {}

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
        context: str = "",
    ) -> AgentResult:
        if not session_id:
            return AgentResult(
                answer="Para hacer un pedido necesito que inicies una conversación.",
                agent_name=self.name,
            )

        state = self._get_state(session_id)
        lower = message.lower().strip()

        # Global cancel / human escalation
        if any(word in lower for word in ["cancelar", "olvídalo", "no quiero", "humano", "agente"]):
            await self._log_action(db, session_id, user_id, "cancel", {"reason": lower})
            self._reset(session_id)
            return AgentResult(
                answer="Checkout cancelado. ¿En qué más puedo ayudarte?",
                agent_name=self.name,
            )

        if state["step"] == "idle":
            await self._log_action(db, session_id, user_id, "start", {})
            state["step"] = "items"
            return AgentResult(
                answer=(
                    "Vamos a crear tu pedido. ¿Qué productos quieres comprar? "
                    "Puedes decirme, por ejemplo: '2 tenis Nike rojos, 1 playera blanca'."
                ),
                agent_name=self.name,
            )

        if state["step"] == "items":
            items = await self._parse_items(db, message)
            if not items:
                return AgentResult(
                    answer=(
                        "No entendí los productos. Dime algo como "
                        "'2 tenis rojos, 1 playera blanca'."
                    ),
                    agent_name=self.name,
                )
            state["items"] = items
            state["step"] = "address"
            await self._log_action(db, session_id, user_id, "set_items", {"items": items})
            return AgentResult(
                answer=f"Agregué {len(items)} producto(s). Ahora escribe tu dirección de envío completa.",
                agent_name=self.name,
            )

        if state["step"] == "address":
            state["shipping_address"] = {"raw": message.strip()}
            total = self._compute_total(state)
            await self._log_action(
                db, session_id, user_id, "set_address", {"total": float(total)}
            )

            if total > self.SPENDING_LIMIT:
                await self._log_action(
                    db, session_id, user_id, "escalate", {"reason": "spending_limit", "total": float(total)}
                )
                self._reset(session_id)
                return AgentResult(
                    answer=(
                        f"El total (${total:.2f}) supera el límite de ${self.SPENDING_LIMIT:.0f}. "
                        "Tu pedido será revisado por un humano."
                    ),
                    agent_name=self.name,
                )

            state["step"] = "confirm"
            summary = self._build_summary(state, total)
            return AgentResult(
                answer=(
                    f"Resumen del pedido:\n{summary}\n\n"
                    f"¿Confirmas la compra? Escribe 'sí, comprar' para confirmar o 'cancelar'."
                ),
                agent_name=self.name,
            )

        if state["step"] == "confirm":
            if any(word in lower for word in ["sí, comprar", "si, comprar", "confirmar", "sí comprar", "si comprar"]):
                return await self._confirm_order(db, session_id, user_id, state)
            if any(word in lower for word in ["no", "cancelar"]):
                await self._log_action(db, session_id, user_id, "cancel", {"at": "confirm"})
                self._reset(session_id)
                return AgentResult(
                    answer="Pedido cancelado. ¿En qué más puedo ayudarte?",
                    agent_name=self.name,
                )
            return AgentResult(
                answer=(
                    "No entendí. Escribe 'sí, comprar' para confirmar tu pedido "
                    "o 'cancelar' para descartarlo."
                ),
                agent_name=self.name,
            )

        # Unknown state — reset
        self._reset(session_id)
        return AgentResult(
            answer="Reinicié el checkout. ¿Qué productos quieres comprar?",
            agent_name=self.name,
        )

    def is_active(self, session_id: str | None) -> bool:
        """Return True if there is a checkout flow in progress for this session."""
        if not session_id:
            return False
        state = self._sessions.get(session_id)
        return state is not None and state.get("step") not in ("idle", "completed") and state.get("step") is not None

    def _get_state(self, session_id: str) -> dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {"step": "idle", "items": [], "shipping_address": None}
        return self._sessions[session_id]

    def _reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    async def _parse_items(self, db: AsyncSession, message: str) -> list[dict[str, Any]]:
        """Extract quantity + product name pairs and resolve products."""
        # Normalize Spanish conjunctions
        text = message.replace(" y ", ", ")
        pattern = re.compile(r"(\d+)\s+(.+?)(?:,|$)")
        matches = pattern.findall(text)
        items: list[dict[str, Any]] = []
        for qty_str, name in matches:
            qty = int(qty_str)
            name = name.strip()
            if qty <= 0 or not name:
                continue
            result = await search_service.search_products(db, query=name, per_page=1)
            product = result["products"][0] if result["products"] else None
            if not product:
                continue
            items.append(
                {
                    "product_id": str(product.id),
                    "name": product.title,
                    "quantity": qty,
                    "price_at_purchase": float(product.price),
                }
            )
        return items

    def _compute_total(self, state: dict[str, Any]) -> Decimal:
        return sum(
            Decimal(str(item["price_at_purchase"])) * item["quantity"]
            for item in state.get("items", [])
        )

    def _build_summary(self, state: dict[str, Any], total: Decimal) -> str:
        lines = []
        for item in state.get("items", []):
            subtotal = Decimal(str(item["price_at_purchase"])) * item["quantity"]
            lines.append(f"- {item['quantity']} x {item['name']} = ${subtotal:.2f}")
        lines.append(f"Total: ${total:.2f}")
        return "\n".join(lines)

    async def _confirm_order(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str | None,
        state: dict[str, Any],
    ) -> AgentResult:
        if not user_id:
            await self._log_action(db, session_id, user_id, "escalate", {"reason": "no_user"})
            self._reset(session_id)
            return AgentResult(
                answer=(
                    "Necesitas iniciar sesión para completar la compra. "
                    "Te cancelé el checkout; inicia sesión y vuelve a intentarlo."
                ),
                agent_name=self.name,
            )

        total = self._compute_total(state)
        if total > self.SPENDING_LIMIT:
            await self._log_action(
                db, session_id, user_id, "escalate", {"reason": "spending_limit", "total": float(total)}
            )
            self._reset(session_id)
            return AgentResult(
                answer=(
                    f"El total (${total:.2f}) supera el límite de ${self.SPENDING_LIMIT:.0f}. "
                    "Tu pedido será revisado por un humano."
                ),
                agent_name=self.name,
            )

        items = [
            OrderItemCreate(product_id=UUID(item["product_id"]), quantity=item["quantity"])
            for item in state["items"]
        ]
        data = OrderCreate(
            items=items,
            shipping_address=state.get("shipping_address"),
        )
        try:
            order = await order_service.create_order(db, UUID(user_id), data)
        except ValueError as exc:
            await self._log_action(db, session_id, user_id, "error", {"message": str(exc)})
            return AgentResult(
                answer=f"No pude crear el pedido: {exc}",
                agent_name=self.name,
            )

        await self._log_action(
            db,
            session_id,
            user_id,
            "create_order",
            {"order_id": str(order.id), "total": float(total)},
        )
        self._reset(session_id)
        return AgentResult(
            answer=(
                f"¡Pedido creado exitosamente! Número de orden: {order.id}. "
                f"Total: ${total:.2f}. Puedes pagarlo desde tu cuenta."
            ),
            agent_name=self.name,
            metadata={"order_id": str(order.id)},
        )

    async def _log_action(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str | None,
        action_type: str,
        details: dict[str, Any],
    ) -> None:
        action = AgentAction(
            session_id=session_id,
            user_id=user_id,
            agent_name=self.name,
            action_type=action_type,
            details=details,
        )
        db.add(action)
        await db.flush()


checkout_agent = CheckoutAgent()
