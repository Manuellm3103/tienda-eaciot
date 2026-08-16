"""Campaign Agent for the AI Marketing Department.

Generates seasonal/lifecycle campaign proposals using the existing campaign
engine data and Mexican holiday calendar.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import date, datetime, timedelta

from app.services.agents.base import BaseAgent, AgentResult
from app.services.campaign_engine import campaign_engine


class CampaignAgent(BaseAgent):
    name = "campaign"

    def _upcoming_holidays(self, days: int = 30) -> dict[str, str]:
        today = date.today()
        end = today + timedelta(days=days)
        upcoming: dict[str, str] = {}
        from app.services import campaign_engine as ce_module

        for event, event_date_str in ce_module.MEXICAN_HOLIDAYS.items():
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
            # Normalize to current year for recurring holidays
            event_date = event_date.replace(year=today.year)
            if today <= event_date <= end:
                upcoming[event] = event_date.isoformat()
        return upcoming

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
        context: str = "",
    ) -> AgentResult:
        lower = message.lower()

        if any(word in lower for word in ["campaña", "campa�a", "email", "promoción", "promocion", "navidad", "buen fin", "cumpleaños"]):
            upcoming = self._upcoming_holidays(days=30)
            holiday_names = ", ".join(upcoming.keys()) if upcoming else "ninguno en los próximos 30 días"

            return AgentResult(
                answer=(
                    "Aquí tienes una propuesta de campaña:\n\n"
                    f"**Próximos eventos MX:** {holiday_names}\n\n"
                    "**Acciones recomendadas:**\n"
                    "1. Segmentar clientes por riesgo de abandono.\n"
                    "2. Ofrecer descuento progresivo (10-20%).\n"
                    "3. Programar 3 emails: anuncio, recordatorio, últimas horas.\n"
                    "4. Medir tasa de apertura y conversión."
                ),
                agent_name=self.name,
                metadata={"upcoming_holidays": upcoming},
            )

        return AgentResult(
            answer="Puedo ayudarte a diseñar campañas para fechas clave como Buen Fin, Navidad o cumpleaños. ¿Qué evento tienes en mente?",
            agent_name=self.name,
        )


campaign_agent = CampaignAgent()
