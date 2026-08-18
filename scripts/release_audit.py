"""Registra la salida de un paso del release en la BD (release_runs).

Canal de observabilidad para Render free (sin Shell): la BD es el único
medio que comprobadamente comparten release y runtime. Cada paso del release
hace pipe de su salida a este script:

    python scripts/bootstrap.py 2>&1 | python scripts/release_audit.py bootstrap

La salida se SANA antes de guardarla: se eliminan los valores de variables
de entorno con nombre sensible (KEY/SECRET/PASSWORD/TOKEN/CSD) para que la
ruta pública GET /release-audit nunca filtre secretos.
"""
import asyncio
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from app.database import async_session  # noqa: E402

MAX_LEN = 2000

_SECRET_NAMES = re.compile(
    r"(KEY|SECRET|PASSWORD|TOKEN|CSD|PRIVATE|CREDENTIAL)",
    re.IGNORECASE,
)


def sanitize(raw: str) -> str:
    out = raw
    for name, value in os.environ.items():
        if value and len(value) > 6 and _SECRET_NAMES.search(name):
            out = out.replace(value, "***")
    return out[-MAX_LEN:]


async def main() -> None:
    script = sys.argv[1] if len(sys.argv) > 1 else "desconocido"
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    raw = raw.strip()
    status = "ok"
    if "FAILED" in raw or "Traceback" in raw or "Error" in raw:
        status = "error"
    msg = sanitize(raw)

    async with async_session() as db:
        await db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS release_runs ("
                "id VARCHAR(36) PRIMARY KEY, "
                "ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "script VARCHAR(50), status VARCHAR(10), message TEXT)"
            )
        )
        await db.execute(
            text(
                "INSERT INTO release_runs (id, script, status, message) "
                "VALUES (:id, :script, :status, :message)"
            ),
            {"id": str(uuid.uuid4()), "script": script, "status": status, "message": msg},
        )
        await db.commit()
    print(f"audit: {script} -> {status}")


if __name__ == "__main__":
    asyncio.run(main())
