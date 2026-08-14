"""Conversational business analytics (#15 on the innovation roadmap).

Answers natural-language questions in Spanish by generating a read-only SQL
query through the dual-LLM router (OpenCode Go is preferred for SQL) and
executing it against SQLite under a strict SELECT-only safety envelope.
"""
import re
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base
from app.ai.llm_router import llm_router, TaskType

# SQLite does not support CALL/EXEC/COPY/LOAD; the extra tokens are belt-and-suspenders.
FORBIDDEN_TOKENS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH", "DETACH",
    "PRAGMA", "REPLACE", "VACUUM", "REINDEX", "TRUNCATE", "MERGE", "GRANT",
    "REVOKE", "CALL", "EXEC", "EXECUTE", "COPY", "LOAD", "RENAME", "RELEASE",
    "SAVEPOINT", "COMMIT", "ROLLBACK", "BEGIN", "END", "ANALYZE",
)

SYSTEM_PROMPT = (
    "Eres un analista de datos de Tienda Eaciot. Conviertes preguntas en "
    "español en consultas SQL de SOLO LECTURA para SQLite. Responde SIEMPRE "
    "con JSON válido."
)


def is_read_only_sql(sql: str) -> bool:
    """Allow only SELECT (or WITH ... SELECT) statements, no writes/DDL."""
    upper = sql.strip().upper().rstrip(";").strip()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return False
    for token in FORBIDDEN_TOKENS:
        if re.search(rf"\b{token}\b", upper):
            return False
    return True


def _serialize(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class AIAnalyticsService:
    def _schema_description(self) -> str:
        lines = []
        for table_name in sorted(Base.metadata.tables.keys()):
            cols = Base.metadata.tables[table_name].columns
            lines.append(f"- {table_name}({', '.join(c.name for c in cols)})")
        return "\n".join(lines)

    async def answer_question(self, db: AsyncSession, question: str) -> dict:
        prompt = (
            f"Esquema de la base de datos (SQLite):\n{self._schema_description()}\n\n"
            f"Pregunta del dueño de la tienda: \"{question}\"\n\n"
            "Genera UNA consulta SQL de solo lectura (SELECT) que responda la "
            "pregunta. No uses INSERT/UPDATE/DELETE ni DDL. Limita resultados a "
            "50 filas. Responde en JSON con estas claves:\n"
            '{"sql": "<consulta>", "chart_type": "<bar|line|pie|table|number>", '
            '"explanation": "<explicación breve en español>"}'
        )
        plan = await llm_router.generate_structured(
            prompt, system=SYSTEM_PROMPT, task_type=TaskType.SQL_GENERATION
        )

        sql = (plan.get("sql") or "").strip().rstrip(";")
        if not sql:
            return {"question": question, "error": "El modelo no devolvió una consulta SQL."}
        if not is_read_only_sql(sql):
            return {
                "question": question,
                "sql": sql,
                "error": "La consulta fue rechazada por no ser de solo lectura.",
            }

        try:
            result = await db.execute(text(sql))
            columns = list(result.keys())
            rows = result.mappings().all()
            data = [
                [_serialize(row[c]) for c in columns]
                for row in rows[:50]
            ]
        except Exception as exc:  # noqa: BLE001 — surface SQL errors to the admin
            return {"question": question, "sql": sql, "error": f"Error SQL: {exc}"}

        return {
            "question": question,
            "sql": sql,
            "chart_type": plan.get("chart_type", "table"),
            "explanation": plan.get("explanation", ""),
            "columns": columns,
            "data": data,
            "row_count": len(data),
        }


ai_analytics = AIAnalyticsService()
