"""AI advisor for invoice data (RFC / CP) during checkout.

Combines the deterministic validator with the dual-LLM router: the validator
is the source of truth, and the LLM turns the findings into a friendly,
actionable Spanish message. If the LLM is down, a deterministic fallback
message is produced so the customer is never left without guidance.
"""
from app.ai.llm_router import llm_router, TaskType
from app.services.rfc_validator import (
    validate_format,
    validate_existence,
    validate_cp,
    normalize,
)


def _fallback_suggestion(rfc_valid: bool, cp_valid: bool, errors: list[str], warnings: list[str], exists) -> str:
    parts: list[str] = []
    if not rfc_valid:
        for e in errors:
            parts.append(e)
    if warnings:
        for w in warnings:
            parts.append(w)
    if rfc_valid and exists is False:
        parts.append("Ese RFC no aparece registrado en el SAT. Verifica que no tenga errores de escritura.")
    if rfc_valid and exists is True:
        parts.append("Tu RFC está registrado en el SAT. ✅")
    if not cp_valid and errors:
        pass  # CP errors appended separately
    return " ".join(parts) if parts else "RFC y código postal válidos."


async def advise(rfc_raw: str, name: str = "", cp: str = "") -> dict:
    """Validate RFC + CP and return structured feedback with an AI message."""
    fmt = validate_format(rfc_raw)
    cp_result = validate_cp(cp)

    exists = None
    if fmt["valid"] and not fmt["is_publico"]:
        exists = await validate_existence(fmt["normalized"])

    errors = fmt["errors"] + cp_result["errors"]
    warnings = fmt["warnings"]

    suggestion = _fallback_suggestion(
        fmt["valid"], cp_result["valid"], errors, warnings, exists
    )

    # Try to enrich with the LLM (best-effort; fall back to deterministic text).
    # Short timeout keeps the checkout snappy even when the LLM backend is down.
    if errors or warnings or exists is False:
        prompt = (
            "Eres un asistente de una tienda en línea mexicana. El cliente capturó estos datos "
            f"para su factura: RFC='{fmt['normalized']}', nombre='{name}', CP='{cp}'. "
            f"Validación: formato_rfc={'válido' if fmt['valid'] else 'inválido'}, "
            f"cp={'válido' if cp_result['valid'] else 'inválido'}, "
            f"rfc_existe_sat={exists if exists is not None else 'desconocido'}, "
            f"errores={errors}, advertencias={warnings}. "
            "Da UNA sugerencia breve y amable en español (máx 2 frases) de cómo corregirlo."
        )
        try:
            import asyncio

            ai_text = await asyncio.wait_for(
                llm_router.generate(
                    prompt,
                    system="Eres un asesor de facturación mexicano, claro y servicial.",
                    task_type=TaskType.GENERAL,
                ),
                timeout=2.5,
            )
            if ai_text and ai_text.strip():
                suggestion = ai_text.strip()
        except Exception:
            pass

    return {
        "rfc": {
            "valid": fmt["valid"],
            "normalized": fmt["normalized"],
            "tipo": fmt["tipo"],
            "is_publico": fmt["is_publico"],
            "exists_at_sat": exists,
            "errors": fmt["errors"],
            "warnings": fmt["warnings"],
        },
        "cp": cp_result,
        "suggestion": suggestion,
    }


invoice_advisor = None  # module-level functions used directly
